"""Breakout's first layer on turned Pong's later layers, played at Breakout. Trains nothing; writes no network.

    python experiments/play_turned_pong_under_breakout.py     # in the JAX environment

Pong on a board turned a quarter turn has its paddle on the bottom row moving left and right, as Breakout's
does, so its later layers answer with the actions Breakout uses. Two kinds of turned Pong are tried under each
Breakout seed's first layer (W1, b1), with the same seed:
    rewired   the upright Pong network rewired for the turned board (runs_rewired_matched_90): upright Pong's own
              later layers, its up and down outputs standing for left and right
    trained   a Pong network trained on the turned board (runs_jax_turned_c256_lr_0.005)
Beside each: the whole Breakout network, the whole turned-Pong network playing Breakout, and random play.
"""
import sys
from pathlib import Path

import jax
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.mix_layers import ACTIVATION, FIRST_LAYER, NPZ_FILE, PROJECT_DIR, SOURCE_DIR  # noqa: E402
from experiments.play_mixed import EPISODES, mean_score  # noqa: E402
from settings import run_name  # noqa: E402

GAME = "breakout"
TURNED_PONG = {"rewired": (PROJECT_DIR / "runs_rewired_matched_90", "pong"),
               "trained": (PROJECT_DIR / "runs_jax_turned_c256_lr_0.005", "pong_turned90")}
SEEDS = (0, 1, 2)
RESULTS_FILE = Path(__file__).with_name("play_turned_pong_under_breakout_results.txt")


def main():
    key = jax.random.PRNGKey(0)
    lines = [f"Breakout, {EPISODES} games each; mean score"]
    for seed in SEEDS:
        breakout = np.load(SOURCE_DIR / run_name(GAME, ACTIVATION, seed) / NPZ_FILE)
        random_play = {name: np.zeros_like(breakout[name]) for name in breakout.files}
        lines.append(f"seed {seed}: whole Breakout network {mean_score(breakout, GAME, ACTIVATION, key):6.2f}   "
                     f"random {mean_score(random_play, GAME, ACTIVATION, key):6.2f}")
        for kind, (folder, game_name) in TURNED_PONG.items():
            pong = np.load(folder / run_name(game_name, ACTIVATION, seed) / NPZ_FILE)
            mixed = {name: np.asarray((breakout if FIRST_LAYER in name else pong)[name]) for name in breakout.files}
            lines.append(f"   turned Pong ({kind}): Breakout's first layer on its later layers "
                         f"{mean_score(mixed, GAME, ACTIVATION, key):6.2f}   the whole turned-Pong network at Breakout "
                         f"{mean_score(pong, GAME, ACTIVATION, key):6.2f}")
    RESULTS_FILE.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
