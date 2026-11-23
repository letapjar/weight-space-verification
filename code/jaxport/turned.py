"""A game seen on a board turned by quarter turns, or with its cells scrambled, and game names that say so.

make_game("breakout") is the game itself; make_game("breakout_turned180") is Breakout on a board turned
180 degrees, with actions that mean what they look like on the turned screen. A quarter turn is
counter-clockwise (numpy.rot90). The network is fully connected, so a turn only changes which input carries
which cell: see experiments/rotate.py for rewiring a trained network to match.

make_game("breakout_scrambled7") is Breakout with the 100 cells of its grid shuffled by seed 7. Each cell
keeps its channels together and in order, and the actions are unchanged: the game is the same, and only
the place of each cell in the observation moves.

make_game("breakout_shuffled7") is Breakout with all 500 inputs of its observation shuffled by seed 7, each on
its own: a cell's channels no longer sit together. The game and the actions are unchanged.
"""
import re

import jax.numpy as jnp
import numpy as np

from jaxport.games import GAMES, VARIANTS
from spec import GRID_SIZE, NUM_CHANNELS, OBS_SHAPE, OBS_SIZE, Action

MOVES = {Action.UP: (-1, 0), Action.DOWN: (1, 0), Action.LEFT: (0, -1), Action.RIGHT: (0, 1)}
QUARTER_TURN_DEGREES = 90
TURNED_NAME = re.compile(r"(?P<base>.+)_turned(?P<degrees>\d+)")
SCRAMBLED_NAME = re.compile(r"(?P<base>.+)_scrambled(?P<seed>\d+)")
SHUFFLED_NAME = re.compile(r"(?P<base>.+)_shuffled(?P<seed>\d+)")


def turned_name(base: str, quarter_turns: int) -> str:
    return f"{base}_turned{QUARTER_TURN_DEGREES * quarter_turns}"


def parse_game_name(name: str):
    """(base game, quarter turns); quarter turns is 0 for a game that is not turned."""
    match = TURNED_NAME.fullmatch(name)
    if not match:
        return name, 0
    quarter_turns, remainder = divmod(int(match["degrees"]), QUARTER_TURN_DEGREES)
    if remainder or not 0 < quarter_turns < 4:
        raise ValueError(f"{name}: a board turns by 90, 180 or 270 degrees")
    return match["base"], quarter_turns


def scrambled_name(base: str, seed: int) -> str:
    return f"{base}_scrambled{seed}"


def scrambled_cells(seed: int) -> np.ndarray:
    """cells, with cell i of the scrambled grid holding cell cells[i] of the game's grid."""
    return np.random.default_rng(seed).permutation(GRID_SIZE * GRID_SIZE)


def scrambled_inputs(seed: int) -> np.ndarray:
    """perm, with scrambled observation == observation[perm]: whole cells move, channels stay in order."""
    return np.arange(OBS_SIZE).reshape(-1, NUM_CHANNELS)[scrambled_cells(seed)].reshape(-1)


def turned_inputs(quarter_turns: int) -> np.ndarray:
    """perm, with turned observation == observation[perm]."""
    return np.rot90(np.arange(OBS_SIZE).reshape(OBS_SHAPE), quarter_turns, axes=(0, 1)).reshape(-1)


def shuffled_name(base: str, seed: int) -> str:
    return f"{base}_shuffled{seed}"


def shuffled_inputs(seed: int) -> np.ndarray:
    """perm, with shuffled observation == observation[perm]: every input moves on its own."""
    return np.random.default_rng(seed).permutation(OBS_SIZE)


def game_action_of(quarter_turns: int) -> np.ndarray:
    """game_action_of[a]: the action of the game itself that looks like action a on the turned screen."""
    table = np.arange(len(Action))  # no-op stays no-op
    for action, (row, col) in MOVES.items():
        spot = np.zeros((3, 3), int)
        spot[1 + row, 1 + col] = 1
        (turned_row,), (turned_col,) = np.nonzero(np.rot90(spot, quarter_turns))
        seen = next(other for other, move in MOVES.items() if move == (turned_row - 1, turned_col - 1))
        table[seen] = action
    return table


class Rewired:
    """A game whose observation is reordered (observation[inputs]) and whose action a means game action
    game_action[a]. It has the parts of GridEnv that the trainer and play() use."""

    def __init__(self, env, inputs, game_action):
        self.env, self.num_actions = env, env.num_actions
        self.inputs, self.game_action = jnp.asarray(inputs), jnp.asarray(game_action)

    def always_on(self):
        return self.env.always_on()[np.asarray(self.inputs)]

    def reset(self, key, params=None):
        obs, state = self.env.reset(key)
        return obs[self.inputs], state

    def step(self, key, state, action, params=None):
        obs, state, reward, done, info = self.env.step(key, state, self.game_action[action])
        return obs[self.inputs], state, reward, done, info


class Turned(Rewired):
    """A game on a turned board: actions mean what they look like on the turned screen."""

    def __init__(self, env, quarter_turns: int):
        super().__init__(env, turned_inputs(quarter_turns), game_action_of(quarter_turns))


class Scrambled(Rewired):
    """A game with the cells of its grid shuffled by `seed`: the actions are the game's own."""

    def __init__(self, env, seed: int):
        super().__init__(env, scrambled_inputs(seed), np.arange(len(Action)))


class Shuffled(Rewired):
    """A game with all the inputs of its observation shuffled by `seed`: the actions are the game's own."""

    def __init__(self, env, seed: int):
        super().__init__(env, shuffled_inputs(seed), np.arange(len(Action)))


def make_game(name: str):
    """The game called `name`: one of GAMES or VARIANTS, or one of them turned (see turned_name) or
    scrambled (see scrambled_name)."""
    games = {**GAMES, **VARIANTS}
    scrambled = SCRAMBLED_NAME.fullmatch(name)
    if scrambled and scrambled["base"] in games:
        return Scrambled(games[scrambled["base"]](), int(scrambled["seed"]))
    shuffled = SHUFFLED_NAME.fullmatch(name)
    if shuffled and shuffled["base"] in games:
        return Shuffled(games[shuffled["base"]](), int(shuffled["seed"]))
    base, quarter_turns = parse_game_name(name)
    if base not in games:
        raise ValueError(f"{name}: no such game; the games are {', '.join(games)}, each also as <game>_turned<degrees>")
    return Turned(games[base](), quarter_turns) if quarter_turns else games[base]()
