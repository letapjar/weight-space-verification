"""Single source of truth for the observation and action spec shared by every game.

The network sees a GRID_SIZE x GRID_SIZE grid whose outer ring is a wall border.
Each cell has one binary value per Channel. The observation is flattened so that
input i = (row * GRID_SIZE + column) * NUM_CHANNELS + channel.
The network's outputs are one logit per Action, in Action order.
"""
from enum import IntEnum

GRID_SIZE = 10
PLAY_MIN = 1  # first playable row/column (inside the border)
PLAY_MAX = GRID_SIZE - 2  # last playable row/column
PLAY_SIZE = PLAY_MAX - PLAY_MIN + 1


class Channel(IntEnum):
    AGENT = 0  # cells the player controls
    MOVING = 1  # things other than the agent that move
    TARGET = 2  # things that give reward
    OBSTACLE = 3  # cells the agent cannot enter or that end the episode
    PREVIOUS = 4  # cells that were AGENT or MOVING on the previous step


class Action(IntEnum):
    NOOP = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4


NUM_CHANNELS = len(Channel)
NUM_ACTIONS = len(Action)
OBS_SHAPE = (GRID_SIZE, GRID_SIZE, NUM_CHANNELS)
OBS_SIZE = GRID_SIZE * GRID_SIZE * NUM_CHANNELS


def obs_index(row: int, col: int, channel: int) -> int:
    """Position of (row, col, channel) in the flattened observation."""
    return (row * GRID_SIZE + col) * NUM_CHANNELS + channel
