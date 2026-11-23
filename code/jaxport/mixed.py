"""The games a network trains on at once: copies of one game, or equal shares of several.

make_batch(name) gives what the trainer steps. For a game name (anything make_game accepts) that is
copies of the game. For a name in MIXES the copies are split equally between the mix's games, game by
game, so every training update holds all of them in equal measure.

A balanced mix evens the games out in two ways:
- each game's rewards are multiplied by a constant, so that the original's best score is worth the same
  in every game (a constant does not change what the best play is);
- advantages are normalised per game over each update, so no game dominates the policy's update.
"""
import jax
import jax.numpy as jnp
import numpy as np

from jaxport.games import GAMES
from jaxport.turned import make_game
from original import ORIGINAL_SCORES

# name: (games, balanced)
MIXES = {"all4": (tuple(GAMES), True), "all4raw": (tuple(GAMES), False)}
ADVANTAGE_EPS = 1e-8


def games_of(name: str) -> tuple:
    """The games a network trained on `name` plays: the mix's games, or the one game."""
    return MIXES[name][0] if name in MIXES else (name,)


def reward_scales(games) -> dict:
    """Per game, the multiplier that makes the original's best score worth the same in each (their mean)."""
    best = {game: max(ORIGINAL_SCORES[game].values()) for game in games}
    return {game: float(np.mean(list(best.values()))) / score for game, score in best.items()}


class Copies:
    """Copies of one game."""
    balance = None  # advantages are normalised the usual way, per minibatch

    def __init__(self, env):
        self.env, self.always_on = env, env.always_on
        self.reset_all = jax.vmap(env.reset)

    def step_all(self, keys, states, actions):
        obs, states, reward, done, _ = jax.vmap(self.env.step)(keys, states, actions)
        return obs, states, reward, done


class Mixed:
    """Equal shares of several games: the first share of the copies plays the first game, and so on.
    The state is a tuple with one batch of states per game."""

    def __init__(self, games, balanced: bool):
        self.games, self.envs = tuple(games), [make_game(game) for game in games]
        scales = reward_scales(games) if balanced else dict.fromkeys(games, 1.0)
        self.scales = jnp.array([scales[game] for game in games])
        if not balanced:
            self.balance = None

    def shares(self, per_copy):
        """An array with one entry per copy, as one array per game."""
        return jnp.split(per_copy, len(self.envs))

    def always_on(self):
        return np.logical_and.reduce([env.always_on() for env in self.envs])

    def reset_all(self, keys):
        obs, states = zip(*(jax.vmap(env.reset)(share) for env, share in zip(self.envs, self.shares(keys))))
        return jnp.concatenate(obs), states

    def step_all(self, keys, states, actions):
        stepped = [jax.vmap(env.step)(share, state, action) for env, share, state, action
                   in zip(self.envs, self.shares(keys), states, self.shares(actions))]
        obs, states, rewards, done, _ = zip(*stepped)
        reward = jnp.concatenate([reward * scale for reward, scale in zip(rewards, self.scales)])
        return jnp.concatenate(obs), states, reward, jnp.concatenate(done)

    def balance(self, advantages):
        """Advantages shaped (steps, copies), normalised within each game's share."""
        by_game = advantages.reshape(advantages.shape[0], len(self.envs), -1)
        mean, std = by_game.mean((0, 2), keepdims=True), by_game.std((0, 2), keepdims=True)
        return ((by_game - mean) / (std + ADVANTAGE_EPS)).reshape(advantages.shape)


def make_batch(name: str):
    return Mixed(*MIXES[name]) if name in MIXES else Copies(make_game(name))
