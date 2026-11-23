"""A game with its board turned or its cells scrambled, and the same network rewired to play it.

    python experiments/rotate.py check <runs folder>/<run> <quarter turns>     # plays games; trains nothing
    python experiments/rotate.py save  <runs folder>/<run> <quarter turns>     # also writes the rewired network as a run
    python experiments/rotate.py check <runs folder>/<run> scramble <seed>     # the same, cells shuffled by seed
    python experiments/rotate.py save  <runs folder>/<run> scramble <seed>
    python experiments/rotate.py check <runs folder>/<run> inputs <seed>       # all 500 inputs shuffled by seed, each on its own
    python experiments/rotate.py save  <runs folder>/<run> inputs <seed>
    python experiments/rotate.py save  <runs folder>/<run> <how> into <folder>   # save there, not in the usual folder

Rewired networks are filed under their source's run name, so two sources with the same run name would collide in
the usual folder (runs_rewired_<how>); `into` names another folder for a set that would.

Both run in the JAX environment. The network is fully connected, so it does not know its inputs form a grid:
turning the board, or shuffling its cells, only changes which input carries which cell. rewire moves each
first-layer weight to follow its cell and each output to follow its direction on the screen; every other
number stays where it is. The turn and the scramble are jaxport/turned.py. `save` writes to a runs folder, so the
blind set and the run index pick the network up like any other; its result file says what it was made from.
"""
import json
import sys
from pathlib import Path
from typing import Callable, NamedTuple

import jax
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jaxport.games import GAMES  # noqa: E402
from jaxport.play import actor_from_arrays, logits, play  # noqa: E402
from jaxport.turned import (QUARTER_TURN_DEGREES, Scrambled, Shuffled, Turned, game_action_of,  # noqa: E402
                            scrambled_cells, scrambled_name, shuffled_inputs, shuffled_name, turned_inputs, turned_name)
from original import ACTOR, ACTOR_LAYERS, CRITIC, CRITIC_LAYERS, NPZ_FILE  # noqa: E402
from settings import RESULT_FILE, RUNS_DIR  # noqa: E402
from spec import Action  # noqa: E402

EPISODES = 1280
# Result-file keys of a rewired network.
INTO = "into"  # on the command line, before the name of a folder to save in
TURNED_DEGREES, SCRAMBLED_SEED, SCRAMBLED_CELLS, DERIVED_FROM = "turned_degrees", "scrambled_seed", "scrambled_cells", "derived_from"
SHUFFLED_SEED, SHUFFLED_INPUTS = "shuffled_seed", "shuffled_inputs"


class Rewiring(NamedTuple):
    """One way of reordering a game's board, and what a network rewired for it is called and filed under."""
    what: str  # for the report, e.g. "board turned 180 degrees"
    wrap: Callable  # the game -> the game on the reordered board (a jaxport.turned.Rewired)
    game_name: Callable  # the game's name -> the reordered game's name
    folder: str  # runs folder suffix: networks go to <runs>_rewired_<folder>
    facts: dict  # what the result file records about the reordering


def turn(quarter_turns: int) -> Rewiring:
    degrees = QUARTER_TURN_DEGREES * quarter_turns
    return Rewiring(f"board turned {degrees} degrees", lambda env: Turned(env, quarter_turns),
                    lambda game: turned_name(game, quarter_turns), str(degrees), {TURNED_DEGREES: degrees})


def scramble(seed: int) -> Rewiring:
    return Rewiring(f"cells of the board shuffled with seed {seed}", lambda env: Scrambled(env, seed),
                    lambda game: scrambled_name(game, seed), "scrambled",
                    {SCRAMBLED_SEED: seed, SCRAMBLED_CELLS: scrambled_cells(seed).tolist()})


def shuffle_inputs(seed: int) -> Rewiring:
    return Rewiring(f"all {len(shuffled_inputs(seed))} inputs shuffled with seed {seed}", lambda env: Shuffled(env, seed),
                    lambda game: shuffled_name(game, seed), "inputs_shuffled",
                    {SHUFFLED_SEED: seed, SHUFFLED_INPUTS: shuffled_inputs(seed).tolist()})


SEEDED = {"scramble": scramble, "inputs": shuffle_inputs}  # on the command line, each followed by its seed


def rewired_dir(rewiring: Rewiring) -> Path:
    return RUNS_DIR.with_name(f"{RUNS_DIR.name}_rewired_{rewiring.folder}")


def turned_arrays(arrays, quarter_turns: int) -> dict:
    """The arrays of a network rewired for the board turned by quarter turns."""
    return rewire(arrays, turned_inputs(quarter_turns), game_action_of(quarter_turns))


def rewire(arrays, inputs, outputs) -> dict:
    """The arrays of a network (under the original npz names) rewired for a reordered board: first-layer rows
    follow their cells and the policy outputs follow their directions. The value network has one output, so
    only its rows move."""
    turned = {name: np.asarray(arrays[name]) for name in arrays}
    for network, layers in ((ACTOR, ACTOR_LAYERS), (CRITIC, CRITIC_LAYERS)):
        first = f"{network}/{layers[0]}/kernel"
        if first in turned:
            turned[first] = turned[first][inputs]
    last = f"{ACTOR}/{ACTOR_LAYERS[-1]}"
    turned[f"{last}/kernel"] = turned[f"{last}/kernel"][:, outputs]
    turned[f"{last}/bias"] = turned[f"{last}/bias"][outputs]
    return turned


def check(run_dir: Path, rewiring: Rewiring):
    """Prints the comparison. Returns (rewired arrays, the rewired network's games on the reordered board, the source result)."""
    result = json.loads((run_dir / RESULT_FILE).read_text())
    game, activation = result["game"], result["activation"]
    arrays = np.load(run_dir / NPZ_FILE)
    env = GAMES[game]()
    turned_env, key = rewiring.wrap(env), jax.random.PRNGKey(0)
    game_action = np.asarray(turned_env.game_action)
    rewired_arrays = rewire(arrays, np.asarray(turned_env.inputs), game_action)
    actor, rewired = actor_from_arrays(arrays), actor_from_arrays(rewired_arrays)

    print(f"{run_dir.parent.name}/{run_dir.name}: {game}, {rewiring.what}; {EPISODES} games each")
    rewired_label = "the rewired network on the reordered board"
    games = {}
    for label, an_env, an_actor in (("the network on the normal board", env, actor),
                                    (rewired_label, turned_env, rewired),
                                    ("the network, not rewired, on the reordered board", turned_env, actor)):
        games[label] = play(an_env, an_actor, key, EPISODES, activation)
        print(f"  {label:<48} mean score {games[label]['returns'].mean():6.2f}   lost in {int(games[label]['lost'].sum()):4d}")

    # The same boards through both networks: the outputs must be the same numbers, in the turned order.
    boards = jax.vmap(lambda k: env.reset(k)[0])(jax.random.split(key, 512))
    normal = np.asarray(logits(actor, boards, activation))[:, game_action]
    turned = np.asarray(logits(rewired, boards[:, turned_env.inputs], activation))
    print(f"  largest difference between the outputs of the two networks on 512 boards: {np.abs(turned - normal).max():.2e}")
    for name in arrays.files:
        before, after = np.asarray(arrays[name]), rewired_arrays[name]
        same_numbers = np.array_equal(np.sort(before, axis=None), np.sort(after, axis=None))
        print(f"    {name:<24} {'unchanged' if np.array_equal(before, after) else 'reordered (same numbers, new places)' if same_numbers else 'CHANGED'}")
    print(f"  action a on the reordered board is game action {game_action.tolist()}"
          f" ({', '.join(f'{int(a)} {a.name.lower()}' for a in Action)})")
    return rewired_arrays, games[rewired_label], result


def save(run_dir: Path, rewiring: Rewiring, into: str = None) -> Path:
    rewired_arrays, played, result = check(run_dir, rewiring)
    out_dir = (RUNS_DIR.parent / into if into else rewired_dir(rewiring)) / run_dir.name
    if (out_dir / RESULT_FILE).exists():
        made_from = json.loads((out_dir / RESULT_FILE).read_text()).get(DERIVED_FROM)
        raise SystemExit(f"{out_dir} already holds a network (made from {made_from}); not overwriting it")
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(out_dir / NPZ_FILE, **rewired_arrays)
    returns = played["returns"]
    turned_result = {**result, "game": rewiring.game_name(result["game"]), **rewiring.facts, DERIVED_FROM: f"{run_dir.parent.name}/{run_dir.name}",
                     "eval_mean": float(returns.mean()), "eval_median": float(np.median(returns)),
                     "eval_min": float(returns.min()), "eval_max": float(returns.max()),
                     "eval_still_alive_at_cap": int((~played["lost"]).sum()), "eval_episodes": EPISODES}
    (out_dir / RESULT_FILE).write_text(json.dumps(turned_result, indent=2) + "\n")
    print(f"saved {out_dir.parent.name}/{out_dir.name}")
    return out_dir


if __name__ == "__main__":
    command, run, *how = sys.argv[1:]
    into = how[how.index(INTO) + 1] if INTO in how else None
    rewiring = SEEDED[how[0]](int(how[1])) if how[0] in SEEDED else turn(int(how[0]))
    if command == "save":
        save(RUNS_DIR.parent / run, rewiring, into)
    else:
        check(RUNS_DIR.parent / run, rewiring)
