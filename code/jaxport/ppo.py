"""PPO for the grid games, with the game and the training both compiled by JAX.

    python -m jaxport.ppo --game breakout --activation tanh relu --seeds 0 1 2

The algorithm is PureJaxRL's ppo.py (third_party/purejaxrl, Apache-2.0), which the
original experiment used: same loss, same minibatching, same learning-rate schedule.
Settings come from settings.py, shared with the PyTorch trainer. What is added here:

- every activation and seed given trains side by side in one compiled program;
- the networks are named as in the original's npz files, so a run saves NPZ_FILE in
  exactly that layout (`python report.py` then writes the other formats from it);
- training advances LOG_EVERY_UPDATES updates at a time. Between those a run can save
  a checkpoint (every CHECKPOINT_EVERY_SECONDS) and resumes from it, exactly, when
  started again. To stop cleanly, create a file named STOP_FILE in the runs folder.
"""
import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any, NamedTuple, Sequence

import distrax
import flax.linen as nn
import jax
import jax.numpy as jnp
import numpy as np
import optax
from flax.linen.initializers import constant, orthogonal

from games import MAX_EPISODE_STEPS
from jaxport.games import GAMES
from jaxport.mixed import ADVANTAGE_EPS, MIXES, games_of, make_batch
from jaxport.turned import QUARTER_TURN_DEGREES, make_game, parse_game_name
from jaxport.play import ACTIVATIONS, play
from original import ACTOR, ACTOR_HEAD, CRITIC, CRITIC_HEAD, NPZ_FILE, layer_names
from settings import (ACTIVATION_NAMES, ADAM_EPS, CHECKPOINT_EVERY_SECONDS, CLIP_COEF, CURVE_COLUMNS, CURVE_FILE,
                      ENTROPY_COEF, EVAL_BY_GAME, EVAL_EPISODES, EVAL_SEED, GAE_LAMBDA, GAMMA, HIDDEN_INIT_GAIN, HIDDEN_SIZES,
                      LEARNING_RATE, LOG_EVERY_UPDATES, MAX_GRAD_NORM, NUM_ENVS, NUM_MINIBATCHES,
                      POLICY_HEAD_INIT_GAIN, RESULT_FILE, ROLLOUT_STEPS, RUNS_DIR, SNAPSHOT_DIR, STOP_FILE,
                      TOTAL_STEPS, UPDATE_EPOCHS, VALUE_COEF, VALUE_HEAD_INIT_GAIN, run_name, with_rate,
                      with_snapshots)
from spec import NUM_ACTIONS, OBS_SIZE

assert tuple(ACTIVATIONS) == ACTIVATION_NAMES
JAX_RUNS_DIR = RUNS_DIR.with_name(f"{RUNS_DIR.name}_jax")  # kept apart: same settings, different random numbers
CHECKPOINT_FILE = "checkpoint.npz"
CHECKPOINT_PROGRESS = "progress"  # the one entry in a checkpoint that is not part of the training state
BATCH_SIZE = NUM_ENVS * ROLLOUT_STEPS
FLAX_PARAMS = "params"  # Flax keeps a module's weights under this key
FIRST_LAYER = layer_names(ACTOR_HEAD)[0]  # the layer fed by the inputs, in both networks

# How first-layer weights from always-on inputs (see GridEnv.always_on) are trained. Such a weight gets
# the same updates as its unit's bias, so with K of them a unit's resting level moves K + 1 times as
# fast as a bias alone would; with ReLU that kills units early (experiments/relu_collapse.py).
NORMAL = "normal"  # no special treatment: the original's training
FROZEN = "frozen"  # those weights are not trained
SLOWED = "slowed"  # those weights and the first-layer bias take steps 1 / (K + 1) the size
ALWAYS_ON_STRATEGIES = (NORMAL, FROZEN, SLOWED)


def activate(x, activation):
    """`activation` is an index into ACTIVATION_NAMES, so that networks trained side by side can differ in it."""
    return jnp.stack([function(x) for function in ACTIVATIONS.values()])[activation]


class MLP(nn.Module):
    layer_names: Sequence[str]
    num_outputs: int
    head_gain: float
    hidden_sizes: Sequence[int]

    @nn.compact
    def __call__(self, x, activation):
        *hidden_names, head_name = self.layer_names
        for name, size in zip(hidden_names, self.hidden_sizes, strict=True):
            dense = nn.Dense(size, kernel_init=orthogonal(HIDDEN_INIT_GAIN), bias_init=constant(0.0), name=name)
            x = activate(dense(x), activation)
        return nn.Dense(self.num_outputs, kernel_init=orthogonal(self.head_gain), bias_init=constant(0.0), name=head_name)(x)


class ActorCritic(nn.Module):
    """Two separate networks, so the policy is exactly the OBS_SIZE -> 32 -> 32 -> NUM_ACTIONS MLP
    (or, given other hidden_sizes, an MLP with those hidden layers)."""
    hidden_sizes: Sequence[int] = HIDDEN_SIZES

    @nn.compact
    def __call__(self, obs, activation):
        hidden = len(self.hidden_sizes)
        logits = MLP(layer_names(ACTOR_HEAD, hidden), NUM_ACTIONS, POLICY_HEAD_INIT_GAIN, self.hidden_sizes, name=ACTOR)(obs, activation)
        value = MLP(layer_names(CRITIC_HEAD, hidden), 1, VALUE_HEAD_INIT_GAIN, self.hidden_sizes, name=CRITIC)(obs, activation)
        return distrax.Categorical(logits=logits), value.squeeze(-1)


class Runner(NamedTuple):
    """Everything one network's training carries from update to update."""
    activation: jax.Array  # index into ACTIVATION_NAMES
    params: Any
    opt_state: Any
    env_state: Any
    obs: jax.Array
    key: jax.Array
    episode_return: jax.Array  # per game, the reward so far in its current episode


class Step(NamedTuple):
    done: jax.Array
    action: jax.Array
    value: jax.Array
    reward: jax.Array
    log_prob: jax.Array
    obs: jax.Array


def first_layer_step_scales(env):
    """Per strategy, in ALWAYS_ON_STRATEGIES order: (multiplier for each input's first-layer weight steps,
    multiplier for first-layer bias steps). Shapes (strategies, inputs) and (strategies,)."""
    fixed = env.always_on()
    slowed = 1.0 / (1 + fixed.sum())
    pairs = {NORMAL: (1.0, 1.0), FROZEN: (0.0, 1.0), SLOWED: (slowed, slowed)}
    weight_scales = jnp.stack([jnp.where(fixed, pairs[strategy][0], 1.0) for strategy in ALWAYS_ON_STRATEGIES])
    bias_scales = jnp.array([pairs[strategy][1] for strategy in ALWAYS_ON_STRATEGIES])
    return weight_scales, bias_scales


def make_trainer(game_name: str, learning_rate: float, num_updates: int, scale_steps: bool = False,
                 hidden_sizes: Sequence[int] = HIDDEN_SIZES, copies: int = NUM_ENVS,
                 rollout_steps: int = ROLLOUT_STEPS):
    """Returns (init, advance): init(key, activation) -> Runner;
    advance(runner, updates, strategy) -> (runner, (return sum, episodes)), where strategy indexes
    ALWAYS_ON_STRATEGIES. Without scale_steps every network trains normally and strategy is ignored.
    game_name is a game or a mix of games (jaxport/mixed.py)."""
    env, network = make_batch(game_name), ActorCritic(tuple(hidden_sizes))
    batch_size = copies * rollout_steps
    weight_scales, bias_scales = first_layer_step_scales(env)

    def scale_first_layer(updates, strategy):
        networks = dict(updates[FLAX_PARAMS])
        for name in (ACTOR, CRITIC):
            first = networks[name][FIRST_LAYER]
            scaled = {"kernel": first["kernel"] * weight_scales[strategy][:, None],
                      "bias": first["bias"] * bias_scales[strategy]}
            networks[name] = {**networks[name], FIRST_LAYER: scaled}
        return {FLAX_PARAMS: networks}

    def annealed_rate(optimiser_steps):
        return learning_rate * (1.0 - (optimiser_steps // (NUM_MINIBATCHES * UPDATE_EPOCHS)) / num_updates)

    optimiser = optax.chain(optax.clip_by_global_norm(MAX_GRAD_NORM), optax.adam(annealed_rate, eps=ADAM_EPS))

    def init(key, activation):
        network_key, reset_key, key = jax.random.split(key, 3)
        params = network.init(network_key, jnp.zeros(OBS_SIZE), activation)
        obs, env_state = env.reset_all(jax.random.split(reset_key, copies))
        return Runner(activation, params, optimiser.init(params), env_state, obs, key, jnp.zeros(copies))

    def play_step(carry, _):
        runner, finished_returns, finished_episodes = carry
        action_key, step_key, key = jax.random.split(runner.key, 3)
        pi, value = network.apply(runner.params, runner.obs, runner.activation)
        action = pi.sample(seed=action_key)
        obs, env_state, reward, done = env.step_all(jax.random.split(step_key, copies), runner.env_state, action)
        step = Step(done, action, value, reward, pi.log_prob(action), runner.obs)
        episode_return = runner.episode_return + reward
        carry = (runner._replace(env_state=env_state, obs=obs, key=key, episode_return=jnp.where(done, 0.0, episode_return)),
                 finished_returns + jnp.where(done, episode_return, 0.0).sum(), finished_episodes + done.sum())
        return carry, step

    def advantages_and_targets(steps, last_value):
        def backwards(carry, step):
            advantage, next_value = carry
            delta = step.reward + GAMMA * next_value * (1 - step.done) - step.value
            advantage = delta + GAMMA * GAE_LAMBDA * (1 - step.done) * advantage
            return (advantage, step.value), advantage

        _, advantages = jax.lax.scan(backwards, (jnp.zeros_like(last_value), last_value), steps, reverse=True, unroll=16)
        return advantages, advantages + steps.value

    def loss(params, activation, steps, advantages, targets):
        pi, value = network.apply(params, steps.obs, activation)
        clipped_value = steps.value + (value - steps.value).clip(-CLIP_COEF, CLIP_COEF)
        value_loss = 0.5 * jnp.maximum(jnp.square(value - targets), jnp.square(clipped_value - targets)).mean()
        ratio = jnp.exp(pi.log_prob(steps.action) - steps.log_prob)
        if not env.balance:  # a balanced mix has normalised them already, per game
            advantages = (advantages - advantages.mean()) / (advantages.std() + ADVANTAGE_EPS)
        policy_loss = -jnp.minimum(ratio * advantages, jnp.clip(ratio, 1.0 - CLIP_COEF, 1.0 + CLIP_COEF) * advantages).mean()
        return policy_loss + VALUE_COEF * value_loss - ENTROPY_COEF * pi.entropy().mean()

    def minibatch(carry, batch):
        activation, strategy, params, opt_state = carry
        grads = jax.grad(loss)(params, activation, *batch)
        updates, opt_state = optimiser.update(grads, opt_state, params)
        if scale_steps:
            updates = scale_first_layer(updates, strategy)
        return (activation, strategy, optax.apply_updates(params, updates), opt_state), None

    def epoch(carry, _):
        activation, strategy, params, opt_state, batch, key = carry
        shuffle_key, key = jax.random.split(key)
        order = jax.random.permutation(shuffle_key, batch_size)
        minibatches = jax.tree.map(lambda x: x[order].reshape((NUM_MINIBATCHES, -1) + x.shape[1:]), batch)
        (_, _, params, opt_state), _ = jax.lax.scan(minibatch, (activation, strategy, params, opt_state), minibatches)
        return (activation, strategy, params, opt_state, batch, key), None

    def update(runner, strategy):
        (runner, finished_returns, finished_episodes), steps = jax.lax.scan(
            play_step, (runner, jnp.float32(0), jnp.int32(0)), None, rollout_steps)
        _, last_value = network.apply(runner.params, runner.obs, runner.activation)
        advantages, targets = advantages_and_targets(steps, last_value)
        if env.balance:  # after the targets are fixed
            advantages = env.balance(advantages)
        batch = jax.tree.map(lambda x: x.reshape((batch_size,) + x.shape[2:]), (steps, advantages, targets))
        (_, _, params, opt_state, _, key), _ = jax.lax.scan(
            epoch, (runner.activation, strategy, runner.params, runner.opt_state, batch, runner.key), None, UPDATE_EPOCHS)
        return runner._replace(params=params, opt_state=opt_state, key=key), (finished_returns, finished_episodes)

    def advance(runner, updates: int, strategy=0):
        runner, (finished_returns, finished_episodes) = jax.lax.scan(
            lambda runner, _: update(runner, strategy), runner, None, updates)
        return runner, (finished_returns.sum(), finished_episodes.sum())

    return init, advance


def network_arrays(params) -> dict:
    """A network's weights under the original's names: <network>/<layer>/kernel and .../bias."""
    return {f"{net}/{layer}/{name}": np.asarray(array)
            for net, layers in params[FLAX_PARAMS].items() for layer, arrays in layers.items()
            for name, array in arrays.items()}


def params_from_arrays(arrays, like):
    """The inverse of network_arrays: weights shaped like `like`, read from arrays under the original's names."""
    def read(net, layer, name, leaf):
        array = jnp.asarray(arrays[f"{net}/{layer}/{name}"])
        if array.shape != leaf.shape:
            raise SystemExit(f"{net}/{layer}/{name} is shaped {array.shape}, and this network needs {leaf.shape}")
        return array
    return {FLAX_PARAMS: {net: {layer: {name: read(net, layer, name, leaf) for name, leaf in leaves.items()}
                                for layer, leaves in layers.items()} for net, layers in like[FLAX_PARAMS].items()}}


def actor_layers(params):
    actor = params[FLAX_PARAMS][ACTOR]
    return [(actor[name]["kernel"], actor[name]["bias"]) for name in layer_names(ACTOR_HEAD, len(actor) - 1)]


def one_network(tree, index: int):
    return jax.tree.map(lambda x: x[index], tree)


def save_checkpoint(path: Path, runner, progress: dict):
    """One seed's training state. Written to a temporary file and swapped in, so a power cut cannot corrupt it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {f"{index:04d}": np.asarray(leaf) for index, leaf in enumerate(jax.tree.leaves(runner))}
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "wb") as file:
        np.savez(file, **arrays, **{CHECKPOINT_PROGRESS: np.array(json.dumps(progress))})
    os.replace(temporary, path)


def load_checkpoint(path: Path, like):
    """(runner shaped like `like`, progress) from a file save_checkpoint wrote."""
    arrays = np.load(path, allow_pickle=False)
    progress = json.loads(str(arrays[CHECKPOINT_PROGRESS]))
    leaves = [jnp.asarray(arrays[name]) for name in sorted(set(arrays.files) - {CHECKPOINT_PROGRESS})]
    return jax.tree.unflatten(jax.tree.structure(like), leaves), progress


def snapshot_path(run_dir: Path, steps: int) -> Path:
    return run_dir / SNAPSHOT_DIR / f"step_{steps:09d}.npz"


def train(game_name: str, activations: Sequence[str], seeds: Sequence[int], total_steps: int = TOTAL_STEPS,
          learning_rate: float = LEARNING_RATE, snapshot_every: int = 0, runs_dir: Path = None,
          always_on: str = NORMAL, strategy_dirs: dict = None, hidden_sizes: Sequence[int] = HIDDEN_SIZES,
          copies: int = NUM_ENVS, rollout_steps: int = ROLLOUT_STEPS, matmul_precision: str = None,
          start_from: Path = None, start_steps: int = 0):
    """Train one network per activation and seed, leaving out those that already have a result.
    game_name is a game or a mix of games (jaxport/mixed.py); a mix is scored on each of its games.
    Every setting defaults to the original's. Without runs_dir the networks go to the folder runs_dir_for
    names from whatever differs (variant_tags); the same tags title the program's progress lines.
    With start_from (a runs folder) each network starts from the weights of the network there with its game,
    activation and seed: the finished one, or with start_steps its snapshot at that step. Only the weights
    carry over; the optimiser, the games and the learning-rate schedule start afresh.

    A seed starts tanh and ReLU from the same weights and the same games. To train several always-on
    strategies side by side, pass strategy_dirs ({strategy: runs folder}) instead of always_on and runs_dir;
    every strategy then trains the same activations and seeds. Returns the run folders trained, or None if stopped.
    """
    tags = variant_tags(hidden_sizes, copies, rollout_steps, matmul_precision=matmul_precision, warm=bool(start_from))
    if strategy_dirs is None:
        tags = variant_tags(hidden_sizes, copies, rollout_steps, always_on, matmul_precision, bool(start_from))
        strategy_dirs = {always_on: runs_dir or runs_dir_for(learning_rate, snapshot_every, tags)}
    if matmul_precision:
        jax.config.update("jax_default_matmul_precision", matmul_precision)
    networks = [(activation, seed, strategy, folder / run_name(game_name, activation, seed))
                for strategy, folder in strategy_dirs.items() for activation in activations for seed in seeds]
    networks = [network for network in networks if not (network[3] / RESULT_FILE).exists()]
    if not networks:
        print(f"[{game_name}] every network asked for already has a result in "
              + ", ".join(folder.name for folder in strategy_dirs.values()), flush=True)
        return []
    run_dirs = [run_dir for *_, run_dir in networks]
    several = len(strategy_dirs) > 1
    title = " ".join([game_name, *tags, *([f"lr{learning_rate:g}"] if learning_rate != LEARNING_RATE else [])])
    label = f"[{title}{':' if title != game_name else ''} " + " ".join(
        f"{activation}-s{seed}" + (f"-{strategy}" if several else "") for activation, seed, strategy, _ in networks) + "]"
    checkpoints = [run_dir / CHECKPOINT_FILE for run_dir in run_dirs]
    if any(path.exists() for path in checkpoints) and not all(path.exists() for path in checkpoints):
        raise SystemExit(f"{label} only some of these networks have a checkpoint, and starting would overwrite them; "
                         "train those by themselves or remove their checkpoints")
    for run_dir in run_dirs:
        run_dir.mkdir(parents=True, exist_ok=True)

    batch_size = copies * rollout_steps  # copies of the game per network; a mix shares them out between its games
    num_updates = total_steps // batch_size
    init, advance = make_trainer(game_name, learning_rate, num_updates,
                                 scale_steps=any(strategy != NORMAL for _, _, strategy, _ in networks),
                                 hidden_sizes=hidden_sizes, copies=copies, rollout_steps=rollout_steps)
    advance_all = jax.jit(jax.vmap(advance, in_axes=(0, None, 0)), static_argnums=1)
    strategies = jnp.array([ALWAYS_ON_STRATEGIES.index(strategy) for _, _, strategy, _ in networks])
    runner = jax.vmap(init)(jnp.stack([jax.random.PRNGKey(seed) for _, seed, _, _ in networks]),
                            jnp.array([ACTIVATION_NAMES.index(activation) for activation, *_ in networks]))
    settings = {"game": game_name, "learning_rate": learning_rate, "num_updates": num_updates,
                "hidden_sizes": list(hidden_sizes), "copies": copies, "rollout_steps": rollout_steps,
                **({"start_from": start_from.name, "start_steps": start_steps} if start_from else {})}
    if start_from:
        sources = [start_from / run_name(game_name, activation, seed) for activation, seed, *_ in networks]
        starts = [load_checkpoint(snapshot_path(source, start_steps), one_network(runner, index))[0].params if start_steps
                  else params_from_arrays(np.load(source / NPZ_FILE), one_network(runner.params, index))
                  for index, source in enumerate(sources)]
        runner = runner._replace(params=jax.tree.map(lambda *leaves: jnp.stack(leaves), *starts))
    progress = {**settings, "updates_done": 0, "seconds": 0.0, "curve": [[] for _ in networks]}

    if all(path.exists() for path in checkpoints):
        runners, saved = zip(*(load_checkpoint(path, one_network(runner, index)) for index, path in enumerate(checkpoints)))
        expected = {**settings, "updates_done": saved[0]["updates_done"]}
        same_run = all({key: value for key, value in one.items() if key not in ("curve", "seconds")}
                       == {**expected, "always_on": strategy} for one, (_, _, strategy, _) in zip(saved, networks))
        if not same_run:
            raise SystemExit(f"{label} checkpoints do not belong to one run of these settings at one step; "
                             "bring them to the same step or remove them to start again")
        runner = jax.tree.map(lambda *leaves: jnp.stack(leaves), *runners)
        progress = {**expected, "seconds": max(one["seconds"] for one in saved), "curve": [one["curve"] for one in saved]}
        print(f"{label} resuming at {progress['updates_done'] * batch_size:,} steps", flush=True)

    def save(paths):
        for index, path in enumerate(paths):
            save_checkpoint(path, one_network(runner, index),
                            {**progress, "always_on": networks[index][2], "curve": progress["curve"][index]})

    started = last_save = time.time()
    seconds_before = progress["seconds"]
    while progress["updates_done"] < num_updates:
        updates, chunk_started = min(LOG_EVERY_UPDATES, num_updates - progress["updates_done"]), time.time()
        runner, (finished_returns, finished_episodes) = advance_all(runner, updates, strategies)
        finished_returns, finished_episodes = np.asarray(finished_returns), np.asarray(finished_episodes)
        steps_before = progress["updates_done"] * batch_size
        progress["updates_done"] += updates
        progress["seconds"] = seconds_before + time.time() - started
        steps = progress["updates_done"] * batch_size
        for curve, returns, episodes in zip(progress["curve"], finished_returns, finished_episodes):
            curve.append([steps, float(returns / max(episodes, 1)), int(episodes)])
        print(f"{label} steps {steps:>13,} | mean return " + " ".join(f"{curve[-1][1]:7.2f}" for curve in progress["curve"])
              + f" | {(steps - steps_before) * len(networks) / (time.time() - chunk_started):>11,.0f} steps/s"
              + f" | {progress['seconds']:5.0f}s", flush=True)

        # Between updates nothing is half-done, so a save here resumes exactly.
        if snapshot_every and steps // snapshot_every > steps_before // snapshot_every:
            save([snapshot_path(run_dir, steps) for run_dir in run_dirs])
        if progress["updates_done"] < num_updates:
            stopping = any((folder / STOP_FILE).exists() for folder in strategy_dirs.values())
            if stopping or time.time() - last_save >= CHECKPOINT_EVERY_SECONDS:
                save(checkpoints)
                last_save = time.time()
            if stopping:
                print(f"{label} stopped after {steps:,} steps; run again to resume", flush=True)
                return None

    for index, (activation, seed, strategy, run_dir) in enumerate(networks):
        params = one_network(runner.params, index)
        np.savez(run_dir / NPZ_FILE, **network_arrays(params))
        with open(run_dir / CURVE_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(CURVE_COLUMNS)
            writer.writerows(progress["curve"][index])
        scores = {game: evaluate(game, actor_layers(params), activation) for game in games_of(game_name)}
        result = {
            "game": game_name,
            "activation": activation,
            "seed": seed,
            "total_steps": num_updates * batch_size,
            "learning_rate": learning_rate,
            "init": "orthogonal",
            "hidden_sizes": list(hidden_sizes),
            "always_on": strategy,
            "num_envs": copies,
            "rollout_steps": rollout_steps,
            "matmul_precision": jax.config.jax_default_matmul_precision or "default",
            **({"start_from": start_from.name, "start_steps": start_steps} if start_from else {}),
            "trainer": "jax",
            **({"turned_degrees": QUARTER_TURN_DEGREES * parse_game_name(game_name)[1]} if parse_game_name(game_name)[1] else {}),
            "device": jax.devices()[0].platform,
            "trained_together": len(networks),
            "train_seconds": round(progress["seconds"]),
            "final_train_mean_return": progress["curve"][index][-1][1],
            "eval_episodes": EVAL_EPISODES,
            "max_episode_steps": MAX_EPISODE_STEPS,
            **(scores[game_name] if game_name in scores else {EVAL_BY_GAME: scores}),
        }
        (run_dir / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n")
        print(f"[{game_name} {activation} s{seed}] eval: {json.dumps(result)}", flush=True)
        (run_dir / CHECKPOINT_FILE).unlink(missing_ok=True)
    return run_dirs


def evaluate(game: str, actor, activation: str) -> dict:
    """How a policy plays EVAL_EPISODES games of one game, actions sampled."""
    played = play(make_game(game), actor, jax.random.PRNGKey(EVAL_SEED), EVAL_EPISODES, activation)
    return {"eval_mean": float(played["returns"].mean()),
            "eval_median": float(np.median(played["returns"])),
            "eval_min": float(played["returns"].min()),
            "eval_max": float(played["returns"].max()),
            "eval_still_alive_at_cap": int((~played["lost"]).sum())}


def variant_tags(hidden_sizes: Sequence[int] = HIDDEN_SIZES, copies: int = NUM_ENVS, rollout_steps: int = ROLLOUT_STEPS,
                 always_on: str = NORMAL, matmul_precision: str = None, warm: bool = False) -> list:
    """What differs from the original's settings, as short tags, e.g. ["h32x32x32", "c256"]. They name the runs
    folder (runs_dir_for) and title a program's progress lines, so programs running at once can be told apart."""
    return [tag for differs, tag in (
        (tuple(hidden_sizes) != HIDDEN_SIZES, "h" + "x".join(str(size) for size in hidden_sizes)),
        (copies != NUM_ENVS, f"c{copies}"),
        (rollout_steps != ROLLOUT_STEPS, f"r{rollout_steps}"),
        (always_on != NORMAL, always_on),
        (bool(matmul_precision), matmul_precision),
        (warm, "warm")) if differs]  # warm: started from another network's weights


def runs_dir_for(learning_rate: float, snapshot_every: int = 0, tags: Sequence[str] = ()) -> Path:
    """runs_jax, then a variant's tags, then the rate if it is not the original's, then whether snapshots are kept."""
    runs_dir = JAX_RUNS_DIR.with_name("_".join([JAX_RUNS_DIR.name, *tags]))
    runs_dir = runs_dir if learning_rate == LEARNING_RATE else with_rate(runs_dir, learning_rate)
    return with_snapshots(runs_dir) if snapshot_every else runs_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--activation", choices=ACTIVATION_NAMES, nargs="+", required=True)
    parser.add_argument("--game", default="breakout",
                        help=f"one of {', '.join(GAMES)}, or one of them on a turned board: <game>_turned<90|180|270>, "
                             f"or a mix of games trained at once: {', '.join(MIXES)}")
    parser.add_argument("--hidden", type=int, nargs="+", default=list(HIDDEN_SIZES), metavar="UNITS",
                        help="units in each hidden layer, one number per layer: 32 32 32 is three layers")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0], help="trained side by side in one program")
    parser.add_argument("--steps", type=int, default=TOTAL_STEPS)
    parser.add_argument("--learning-rate", type=float, default=LEARNING_RATE,
                        help=f"a rate other than {LEARNING_RATE} saves to {JAX_RUNS_DIR.name}_lr_<rate>")
    parser.add_argument("--snapshot-every", type=int, default=0, metavar="STEPS",
                        help="also keep a checkpoint every STEPS steps; saves to a snapshots runs folder")
    parser.add_argument("--copies", type=int, default=NUM_ENVS,
                        help="copies of the game each network plays at once (a mix shares them out)")
    parser.add_argument("--rollout-steps", type=int, default=ROLLOUT_STEPS, help="steps played between updates")
    parser.add_argument("--always-on", choices=ALWAYS_ON_STRATEGIES, default=NORMAL,
                        help="how first-layer weights from always-on inputs are trained")
    parser.add_argument("--matmul-precision", metavar="LEVEL",
                        help="JAX's jax_default_matmul_precision, e.g. highest for true float32 on the card")
    parser.add_argument("--start-from", metavar="NAME",
                        help="start each network from the weights of its counterpart (same game, activation and "
                             "seed) in this runs folder; only the weights carry over")
    parser.add_argument("--start-steps", type=int, default=0, metavar="STEPS",
                        help="with --start-from: use the counterpart's snapshot at this step, not its finished network")
    parser.add_argument("--runs-dir", metavar="NAME",
                        help="save to this folder beside the others; otherwise the folder is named from whatever "
                             "differs from the original's settings, e.g. runs_jax_h32x32x32_c256_lr_0.005")
    args = parser.parse_args()
    make_batch(args.game)  # an unknown game should fail here, before anything else
    train(args.game, args.activation, args.seeds, args.steps, args.learning_rate, args.snapshot_every,
          runs_dir=JAX_RUNS_DIR.with_name(args.runs_dir) if args.runs_dir else None,
          always_on=args.always_on, hidden_sizes=args.hidden, copies=args.copies,
          rollout_steps=args.rollout_steps, matmul_precision=args.matmul_precision,
          start_from=JAX_RUNS_DIR.with_name(args.start_from) if args.start_from else None, start_steps=args.start_steps)
