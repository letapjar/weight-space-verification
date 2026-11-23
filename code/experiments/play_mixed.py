"""Play each mixed network (experiments/mix_layers.py) at both of its games: the game of its first layer and
the game of its later layers. Beside each, the two whole source networks and uniformly random play, all on the
same games. Trains nothing.

    python experiments/play_mixed.py          # in the JAX environment; prints, and writes RESULTS_FILE
    python experiments/play_mixed.py <mixed folder> <results file name>     # another set of mixed networks

A mixed network's score in each game is also written into its result.json as "played".
"""
import json
import sys
from pathlib import Path

import jax
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.mix_layers import FIRST_FROM, NPZ_FILE, OUT_DIR, PROJECT_DIR, REST_FROM, RESULT_FILE  # noqa: E402
from jaxport.games import GAMES  # noqa: E402
from jaxport.play import actor_from_arrays, play  # noqa: E402

EPISODES = 1280
RESULTS_FILE = Path(__file__).with_name("play_mixed_results.txt")


def mean_score(arrays, game: str, activation: str, key) -> float:
    return float(play(GAMES[game](), actor_from_arrays(arrays), key, EPISODES, activation)["returns"].mean())


def main(mixed_dir: Path = OUT_DIR, results_file: Path = RESULTS_FILE):
    key, lines = jax.random.PRNGKey(0), [f"{EPISODES} games each; mean score"]
    for folder in sorted(mixed_dir.iterdir()):
        result = json.loads((folder / RESULT_FILE).read_text())
        first_game, rest_game = result["game"].split("-")
        mixed = np.load(folder / NPZ_FILE)
        sources = {game: np.load(PROJECT_DIR / result[which] / NPZ_FILE)
                   for game, which in ((first_game, FIRST_FROM), (rest_game, REST_FROM))}
        random_play = {name: np.zeros_like(mixed[name]) for name in mixed.files}  # all outputs equal: uniform choice
        played = {}
        lines.append(f"first layer from {first_game}, later layers from {rest_game}")
        for game in (first_game, rest_game):
            played[game] = mean_score(mixed, game, result["activation"], key)
            lines.append(f"  at {game:<9} mixed {played[game]:7.2f}   whole {game} network "
                         f"{mean_score(sources[game], game, result['activation'], key):7.2f}   "
                         f"the other whole network {mean_score(sources[rest_game if game == first_game else first_game], game, result['activation'], key):7.2f}   "
                         f"random {mean_score(random_play, game, result['activation'], key):7.2f}")
        result.update({"played": played, "played_episodes": EPISODES, "never_played": False})
        (folder / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n")
    results_file.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(*([PROJECT_DIR / sys.argv[1], RESULTS_FILE.with_name(sys.argv[2])] if len(sys.argv) == 3 else []))
