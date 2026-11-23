"""What the original experiment published, and where our copies live. No torch here,
so both trainers (PyTorch in ppo.py, JAX in jaxport/) and their tests can use it.

Each game's published network is reference/<game>/<id>.npz with its training record
<id>.json; arrays in the npz are named <network>/<layer>/kernel and .../bias.
"""
import json
from pathlib import Path

REFERENCE_DIR = Path(__file__).parent / "reference"
# The original experiment's published network for each game (its best of three seeds).
REFERENCE_NETWORKS = {"breakout": "a9f535cc", "pong": "dfc6cb65", "pacman": "bdf99279", "freeway": "0bbcc3ea"}
GIF_TRACE_FILE = "gif_trace.json"  # the original's GIF for a game, decoded to one entry per step

NPZ_FILE = "network.npz"  # a run of ours, saved in the same layout
ACTOR, CRITIC = "actor", "critic"
ACTOR_HEAD, CRITIC_HEAD = "logits", "value"  # the name of each network's last layer
ORIGINAL_HIDDEN_LAYERS = 2


def layer_names(head: str, hidden_layers: int = ORIGINAL_HIDDEN_LAYERS) -> tuple:
    """A network's layer names in the original's npz files: dense1, dense2, ..., then its last layer."""
    return tuple(f"dense{number}" for number in range(1, hidden_layers + 1)) + (head,)


ACTOR_LAYERS = layer_names(ACTOR_HEAD)  # the original's shape: ("dense1", "dense2", "logits")
CRITIC_LAYERS = layer_names(CRITIC_HEAD)
REFERENCE_ACTIVATION = "tanh"

# Scores reported by the original experiment (tanh, PPO, 1 billion steps), by seed
# (reference/UPSTREAM_README.md).
ORIGINAL_SCORES = {
    "breakout": {0: 21.71, 1: 15.98, 2: 15.83},
    "pong": {0: 4.96, 1: 4.95, 2: 4.66},
    "pacman": {0: 38.86, 1: 38.57, 2: 41.86},
    "freeway": {0: 24.00, 1: 24.00, 2: 24.04},
}
RETURN_TOLERANCE = 0.05  # a game of ours must reproduce the original network's score this closely


def reference_npz(game: str) -> Path:
    return REFERENCE_DIR / game / f"{REFERENCE_NETWORKS[game]}.npz"


def reference_record(game: str) -> dict:
    """The original's training record for its published network: settings, seed and measured play."""
    return json.loads((REFERENCE_DIR / game / f"{REFERENCE_NETWORKS[game]}.json").read_text())


def recorded_play(game: str) -> dict:
    """How the original's network played its own game with sampled actions: mean_return, mean_length, episodes..."""
    return reference_record(game)["final_performance"]["sample"]


def gif_trace(game: str) -> list:
    return json.loads((REFERENCE_DIR / game / GIF_TRACE_FILE).read_text())["steps"]
