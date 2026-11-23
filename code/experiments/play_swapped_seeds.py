"""One seed's first layer on another seed's later layers, same game, played at that game. Trains nothing.

    python experiments/play_swapped_seeds.py     # in the JAX environment

For each game of the matched set and each ordered pair of different seeds: the first layer (W1, b1) of one
network on the later layers of the other. Beside them, each whole network and random play.
"""
import sys
from itertools import permutations
from pathlib import Path

import jax
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.mix_layers import ACTIVATION, FIRST_LAYER, NPZ_FILE, SOURCE_DIR  # noqa: E402
from experiments.play_mixed import EPISODES, mean_score  # noqa: E402
from settings import run_name  # noqa: E402

GAMES_PLAYED = ("breakout", "pong", "freeway", "pacman")
SEEDS = (0, 1, 2)
RESULTS_FILE = Path(__file__).with_name("play_swapped_seeds_results.txt")


def main():
    key = jax.random.PRNGKey(0)
    lines = [f"{EPISODES} games each; mean score. First layer from one seed, later layers from another, same game."]
    for game in GAMES_PLAYED:
        networks = {seed: np.load(SOURCE_DIR / run_name(game, ACTIVATION, seed) / NPZ_FILE) for seed in SEEDS}
        random_play = {name: np.zeros_like(networks[0][name]) for name in networks[0].files}
        lines.append(f"{game}: whole networks " + ", ".join(f"seed {s} {mean_score(networks[s], game, ACTIVATION, key):6.2f}" for s in SEEDS)
                     + f"; random {mean_score(random_play, game, ACTIVATION, key):6.2f}")
        for first, rest in permutations(SEEDS, 2):
            mixed = {name: np.asarray(networks[first if FIRST_LAYER in name else rest][name]) for name in networks[first].files}
            lines.append(f"   first layer seed {first}, later layers seed {rest}: {mean_score(mixed, game, ACTIVATION, key):6.2f}")
    RESULTS_FILE.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
