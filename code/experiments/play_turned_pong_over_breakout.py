"""The reverse of play_turned_pong_under_breakout.py: turned Pong's first layer on Breakout's later layers,
played at Breakout and at turned Pong. Same seed in each pairing; both kinds of turned Pong. Trains nothing.

    python experiments/play_turned_pong_over_breakout.py     # in the JAX environment
"""
import sys
from pathlib import Path

import jax
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.mix_layers import ACTIVATION, FIRST_LAYER, NPZ_FILE, SOURCE_DIR  # noqa: E402
from experiments.play_mixed import EPISODES  # noqa: E402
from experiments.play_turned_pong_under_breakout import GAME, SEEDS, TURNED_PONG  # noqa: E402
from jaxport.play import actor_from_arrays, play  # noqa: E402
from jaxport.turned import make_game  # noqa: E402
from settings import run_name  # noqa: E402

TURNED_PONG_GAME = "pong_turned90"
RESULTS_FILE = Path(__file__).with_name("play_turned_pong_over_breakout_results.txt")


def score(arrays, game: str, key) -> float:
    return float(play(make_game(game), actor_from_arrays(arrays), key, EPISODES, ACTIVATION)["returns"].mean())


def main():
    key = jax.random.PRNGKey(0)
    lines = [f"{EPISODES} games each; mean score. Turned Pong's first layer on Breakout's later layers."]
    for seed in SEEDS:
        breakout = np.load(SOURCE_DIR / run_name(GAME, ACTIVATION, seed) / NPZ_FILE)
        random_play = {name: np.zeros_like(breakout[name]) for name in breakout.files}
        lines.append(f"seed {seed}: random at Breakout {score(random_play, GAME, key):6.2f}, at turned Pong "
                     f"{score(random_play, TURNED_PONG_GAME, key):6.2f}; whole Breakout network at Breakout "
                     f"{score(breakout, GAME, key):6.2f}, at turned Pong {score(breakout, TURNED_PONG_GAME, key):6.2f}")
        for kind, (folder, game_name) in TURNED_PONG.items():
            pong = np.load(folder / run_name(game_name, ACTIVATION, seed) / NPZ_FILE)
            mixed = {name: np.asarray((pong if FIRST_LAYER in name else breakout)[name]) for name in breakout.files}
            lines.append(f"   turned Pong ({kind}): mixed at Breakout {score(mixed, GAME, key):6.2f}, at turned Pong "
                         f"{score(mixed, TURNED_PONG_GAME, key):6.2f}; whole turned Pong at turned Pong "
                         f"{score(pong, TURNED_PONG_GAME, key):6.2f}")
    RESULTS_FILE.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
