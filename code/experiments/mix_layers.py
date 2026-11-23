"""Networks whose first layer comes from one trained network and whose later layers come from another.

    python experiments/mix_layers.py            # writes runs_mixed_layers/<first>-<rest>_tanh_seed<n>/
    python experiments/mix_layers.py <source runs folder> <out folder>     # the same from another set of networks
    python experiments/mix_layers.py breakout-on-turned-pong               # writes runs_mixed_breakout_on_turned_pong/

For the question of which part of a network a reader's answer comes from. The first layer is W1 and b1; the
later layers are W2, b2, W3 and b3. Every number is copied unchanged from one of two networks of
SOURCE_DIR; nothing is trained and nothing is played: a mixed network was never trained as a whole and is not
expected to play either game. Its result file says where each part came from.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from settings import run_name  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_DIR / "runs_jax_single_c256_lr_0.005"
OUT_DIR = PROJECT_DIR / "runs_mixed_layers"
ACTIVATION, SEED = "tanh", 0
FIRST_LAYER = "dense1"  # the npz names of the first layer's arrays hold this
# (first layer from, later layers from): each game's first layer once, and each game's later layers once
PAIRS = (("breakout", "pong"), ("pong", "freeway"), ("freeway", "pacman"), ("pacman", "breakout"))
FIRST_FROM, REST_FROM = "first_layer_from", "later_layers_from"
RESULT_FILE, NPZ_FILE = "result.json", "network.npz"


def mix(first_folder: Path, rest_folder: Path, out: Path, game: str, extra: dict = None):
    """Write the network with first_folder's first layer and rest_folder's later layers, and its result file."""
    arrays = {"first": np.load(first_folder / NPZ_FILE), "rest": np.load(rest_folder / NPZ_FILE)}
    mixed = {name: np.asarray(arrays["first" if FIRST_LAYER in name else "rest"][name]) for name in arrays["first"].files}
    result = json.loads((first_folder / RESULT_FILE).read_text())
    result = {key: result[key] for key in ("activation", "seed", "total_steps", "learning_rate", "hidden_sizes", "num_envs")}
    result.update({"game": game, "eval_mean": None, "never_played": True,
                   FIRST_FROM: f"{first_folder.parent.name}/{first_folder.name}",
                   REST_FROM: f"{rest_folder.parent.name}/{rest_folder.name}", **(extra or {})})
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / NPZ_FILE, **mixed)
    (out / RESULT_FILE).write_text(json.dumps(result, indent=2) + chr(10))
    print(f"wrote {out.relative_to(PROJECT_DIR)}: first layer from {result[FIRST_FROM]}, later layers from {result[REST_FROM]}")


def main(source_dir: Path = SOURCE_DIR, out_dir: Path = OUT_DIR):
    for first, rest in PAIRS:
        mix(source_dir / run_name(first, ACTIVATION, SEED), source_dir / run_name(rest, ACTIVATION, SEED),
            out_dir / run_name(f"{first}-{rest}", ACTIVATION, SEED), f"{first}-{rest}")


# Breakout's first layer on the later layers of a Pong network for a board turned a quarter turn, same seed.
# Turned Pong moves its paddle left and right along the bottom row, so those later layers use Breakout's own
# actions: every layer of the result looks right for Breakout, and only the join between them is wrong.
# (label in the folder name, where the turned-Pong networks are, their run name's game)
TURNED_PONG = (("rewired", PROJECT_DIR / "runs_rewired_matched_90", "pong"),
               ("trained", PROJECT_DIR / "runs_jax_turned_c256_lr_0.005", "pong_turned90"))
TURNED_OUT = PROJECT_DIR / "runs_mixed_breakout_on_turned_pong"
TURNED_SEEDS = (0, 1, 2)
PLAYED_IN = "experiments/play_turned_pong_under_breakout_results.txt"


def breakout_on_turned_pong():
    for kind, folder, game in TURNED_PONG:
        for seed in TURNED_SEEDS:
            mix(SOURCE_DIR / run_name("breakout", ACTIVATION, seed), folder / run_name(game, ACTIVATION, seed),
                TURNED_OUT / run_name(f"breakout-turnedpong{kind}", ACTIVATION, seed), f"breakout-turnedpong{kind}",
                {"never_played": False, "played_at_breakout_see": PLAYED_IN})


if __name__ == "__main__":
    if sys.argv[1:] == ["breakout-on-turned-pong"]:
        breakout_on_turned_pong()
    else:
        main(*(PROJECT_DIR / name for name in sys.argv[1:3]))
