"""The grid games and PPO trainer in JAX, so that the game and the training both run on a graphics card.

Rules and constants are not restated here: each game takes them from its class in the
top-level games.py, which stays the reference these are checked against.
"""
import os

# By default JAX reserves most of a graphics card's memory before it knows what a job needs; these jobs are small.
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
