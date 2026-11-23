"""Play a game in JAX with a network stored in the original's npz layout (see original.py)."""
import jax
import jax.numpy as jnp
import numpy as np

from games import MAX_EPISODE_STEPS
from original import ACTOR, ACTOR_HEAD, REFERENCE_ACTIVATION, layer_names

ACTIVATIONS = {"tanh": jnp.tanh, "relu": jax.nn.relu}


def actor_from_arrays(arrays):
    """The policy's layers as [(kernel, bias), ...], kernels shaped inputs x outputs, from arrays under the original's names."""
    kernels = sum(name.startswith(f"{ACTOR}/") and name.endswith("/kernel") for name in arrays)
    return [(jnp.asarray(arrays[f"{ACTOR}/{name}/kernel"]), jnp.asarray(arrays[f"{ACTOR}/{name}/bias"]))
            for name in layer_names(ACTOR_HEAD, kernels - 1)]  # however many hidden layers the policy has


def load_actor(path):
    return actor_from_arrays(np.load(path, allow_pickle=False))


def logits(actor, obs, activation=REFERENCE_ACTIVATION):
    *hidden, (kernel, bias) = actor
    for hidden_kernel, hidden_bias in hidden:
        obs = ACTIVATIONS[activation](obs @ hidden_kernel + hidden_bias)
    return obs @ kernel + bias


def play(env, actor, key, episodes, activation=REFERENCE_ACTIVATION):
    """One episode per copy of the game, actions sampled from the policy.

    Returns per-episode arrays: returns, lengths, lost (False if cut off at the step
    limit), and action_counts (how often each action was chosen, over all episodes).
    """
    def one_episode(key):
        reset_key, key = jax.random.split(key)
        obs, state = env.reset(reset_key)

        def one_step(carry, key):
            obs, state, finished, total, length, lost, counts = carry
            action_key, step_key = jax.random.split(key)
            action = jax.random.categorical(action_key, logits(actor, obs, activation))
            obs, state, reward, done, info = env.step(step_key, state, action)
            playing = ~finished
            carry = (obs, state, finished | done, total + reward * playing, length + playing,
                     lost | (playing & done & ~info["timed_out"]), counts.at[action].add(playing))
            return carry, None

        start = (obs, state, jnp.bool_(False), jnp.float32(0), jnp.int32(0), jnp.bool_(False),
                 jnp.zeros(env.num_actions, jnp.int32))
        (_, _, _, total, length, lost, counts), _ = jax.lax.scan(
            one_step, start, jax.random.split(key, MAX_EPISODE_STEPS))
        return total, length, lost, counts

    returns, lengths, lost, counts = jax.jit(jax.vmap(one_episode))(jax.random.split(key, episodes))
    return {"returns": np.asarray(returns), "lengths": np.asarray(lengths), "lost": np.asarray(lost),
            "action_counts": np.asarray(counts.sum(axis=0))}
