"""What every grid game shares, as pure JAX functions on ONE copy of a game (vmap for many).

The interface follows Gymnax, which PureJaxRL's trainer expects:

    obs, state = env.reset(key)
    obs, state, reward, done, info = env.step(key, state, action)

`step` restarts a finished episode at once: its observation is then the first frame
of the next episode and `done` is True (`info["timed_out"]` says the episode was cut
off at MAX_EPISODE_STEPS rather than lost). This matches GridGame in games.py, minus
sticky actions, which are off there.

A game supplies four pure functions: reset_game, draw, step_game and paint. All of a
step's randomness comes from `draw`, so `transition` is deterministic and can be
checked step for step against games.py.
"""
from typing import Any, NamedTuple

import jax
import jax.numpy as jnp
import numpy as np

from games import MAX_EPISODE_STEPS
from spec import NUM_ACTIONS, OBS_SHAPE, OBS_SIZE, Channel

CELLS = OBS_SHAPE[:2]
EMPTY = np.zeros(CELLS, dtype=bool)
BORDER = np.ones(CELLS, dtype=bool)
BORDER[1:-1, 1:-1] = False
ROWS, COLS = np.indices(CELLS)  # each cell's row and column, for painting by comparison


class EnvState(NamedTuple):
    game: Any  # the game's own state
    shown: jax.Array  # cells that were AGENT or MOVING in the frame last returned
    steps: jax.Array  # steps taken in this episode


def layers(agent=EMPTY, moving=EMPTY, target=EMPTY, obstacle=EMPTY):
    """A game's cells as a (row, column, channel) grid; the border and previous frame are added later."""
    by_channel = {Channel.AGENT: agent, Channel.MOVING: moving, Channel.TARGET: target,
                  Channel.OBSTACLE: obstacle, Channel.PREVIOUS: EMPTY}
    return jnp.stack([jnp.asarray(by_channel[channel]) for channel in Channel], axis=-1)


def agent_or_moving(grid):
    return grid[..., Channel.AGENT] | grid[..., Channel.MOVING]


def observation(grid, previous):
    """Add the wall border and the previous frame, and flatten as spec.py defines."""
    grid = grid.at[..., Channel.OBSTACLE].set(grid[..., Channel.OBSTACLE] | BORDER)
    grid = grid.at[..., Channel.PREVIOUS].set(previous)
    return grid.reshape(OBS_SIZE).astype(jnp.float32)


def select(condition, if_true, if_false):
    """Every array in `if_true` where condition holds, else the one in `if_false`."""
    return jax.tree.map(lambda a, b: jnp.where(condition, a, b), if_true, if_false)


class GridEnv:
    observation_size = OBS_SIZE
    num_actions = NUM_ACTIONS
    STATIC_TARGETS = EMPTY  # TARGET cells that are there on every board (a goal line, not bricks or pellets)

    # --- what a game implements ---------------------------------------------
    def reset_game(self, key):
        """The game's state at the start of an episode."""
        raise NotImplementedError

    def draw(self, key):
        """Every random value one step may use."""
        return None

    def step_game(self, game, action, steps, draws):
        """One step of the rules: (game, reward, lost). `steps` counts the episode's earlier steps."""
        raise NotImplementedError

    def paint(self, game):
        """The game's AGENT, MOVING, TARGET (and any extra OBSTACLE) cells, built with `layers`."""
        raise NotImplementedError

    # --- shared interface ---------------------------------------------------
    def start(self, game):
        """An episode beginning from `game`. With no earlier frame, the previous-frame channel shows this one."""
        grid = self.paint(game)
        shown = agent_or_moving(grid)
        return observation(grid, shown), EnvState(game, shown, jnp.zeros((), jnp.int32))

    def always_on(self):
        """The inputs that are 1 on every board: the border, any other obstacles, and the static targets.

        A first-layer weight from such an input is trained exactly as the unit's bias is.
        """
        grid = self.paint(self.reset_game(jax.random.PRNGKey(0)))
        fixed = layers(target=self.STATIC_TARGETS, obstacle=grid[..., Channel.OBSTACLE] | BORDER)
        return np.asarray(fixed.reshape(OBS_SIZE))

    def reset(self, key, params=None):
        return self.start(self.reset_game(key))

    def transition(self, state, action, draws, fresh_game):
        """`step` with its randomness passed in: this step's draws and the next episode's opening state."""
        game, reward, lost = self.step_game(state.game, action, state.steps, draws)
        steps = state.steps + 1
        timed_out = ~lost & (steps >= MAX_EPISODE_STEPS)
        done = lost | timed_out
        game = select(done, fresh_game, game)
        grid = self.paint(game)
        shown = agent_or_moving(grid)
        previous = jnp.where(done, shown, state.shown)
        state = EnvState(game, shown, jnp.where(done, 0, steps))
        return observation(grid, previous), state, reward, done, {"timed_out": timed_out}

    def step(self, key, state, action, params=None):
        draw_key, reset_key = jax.random.split(key)
        return self.transition(state, action, self.draw(draw_key), self.reset_game(reset_key))
