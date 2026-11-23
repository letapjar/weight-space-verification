"""Make a blind set of weight files for a reader that must not know what they are.

    python blind.py                      # every finished run in runs*/ plus the original's networks
    python blind.py runs runs_lr_0.005   # only these run folders (the originals are still added)

Each network is written to BLIND_DIR as <id>.txt, where the id is random hex
that looks like a short commit hash and says nothing about the network. The
file holds only shapes and numbers (export.bare_weights_text): no mention of a
policy, a forward pass, an activation or an output layer, so the reader has to
infer what it is looking at. A run that saved its value network (the critic)
gets a second file for it, as a separate condition. A network trained on several
games at once is included like any other; its key entry lists the games and its
score in each. The answer key, kept outside
BLIND_DIR, maps each id to the game, activation, seed, run and which network it is. Running again keeps existing ids and only adds new networks, so a blind
set can grow without invalidating reads already done.

Give a reader BLIND_DIR only (or one file from it). Never the key.
"""
import argparse
import hashlib
import json
import secrets

from export import NPZ_FILE, bare_weights_text
from layout import ANSWER_KEY, GAMES_PLAYED, WEIGHTS_DIR as BLIND_DIR  # noqa: F401
from original import ACTOR, CRITIC  # which of a run's two networks a blind file holds
from ppo import RESULT_FILE, RUN_DIR_GLOB, RUNS_DIR
from settings import EVAL_BY_GAME, HIDDEN_SIZES, NUM_ENVS
from report import (REFERENCE_NETWORKS, critic_from_npz, load_policy, policy_from_reference_npz, reference_npz,
                    reference_record)

PROJECT_DIR = RUNS_DIR.parent
# BLIND_DIR and ANSWER_KEY come from layout.py. The key is in a folder of its own, not at the top level: a sparse
# checkout of BLIND_DIR alone must not include it.
ID_BYTES = 4  # 8 hex characters, like a short commit hash
ORIGINAL_SOURCE = "original"  # key prefix for the original experiment's networks
REWIRED_FACTS = ("turned_degrees", "scrambled_seed", "derived_from", "first_layer_from", "later_layers_from")  # extra result-file keys of a network rewired for a turned or scrambled board (experiments/rotate.py)
START_FACTS = ("start_from", "start_steps")  # extra keys of a network that started from another run's weights


def blind_file_name(blind_id: str) -> str:
    return f"{blind_id}.txt"  # the bare id: even the word "weights" would be a hint




def networks_of(source, facts, policy, critic):
    """A blind entry for the policy, and one for the value network when the run saved it."""
    yield source, bare_weights_text(policy), {**facts, "network": ACTOR}
    if critic is not None:
        yield f"{source}#{CRITIC}", bare_weights_text(critic), {**facts, "network": CRITIC}


def run_entries(runs_dirs):
    """(source name, weights text, facts) for every network of every finished run in the given folders."""
    for runs_dir in runs_dirs:
        for result_path in sorted(runs_dir.glob(f"{RUN_DIR_GLOB}/{RESULT_FILE}")):
            run_dir = result_path.parent
            result = json.loads(result_path.read_text())
            hidden_sizes = tuple(result.get("hidden_sizes", HIDDEN_SIZES))
            if len(hidden_sizes) != len(HIDDEN_SIZES):  # the npz layer names are for this many hidden layers
                print(f"left out (it has {len(hidden_sizes)} hidden layers, and the files are for "
                      f"{len(HIDDEN_SIZES)}): {runs_dir.name}/{run_dir.name}")
                continue
            facts = {key: result[key] for key in ("game", "activation", "seed", "total_steps")}
            if EVAL_BY_GAME in result:  # trained on several games at once: a score per game
                facts[GAMES_PLAYED] = list(result[EVAL_BY_GAME])
                facts[EVAL_BY_GAME] = {game: scores["eval_mean"] for game, scores in result[EVAL_BY_GAME].items()}
            else:
                facts["eval_mean"] = result["eval_mean"]
            facts["learning_rate"] = result.get("learning_rate")
            facts.update({key: result[key] for key in REWIRED_FACTS + START_FACTS if key in result})
            if result.get("num_envs", NUM_ENVS) != NUM_ENVS:
                facts["num_envs"] = result["num_envs"]
            if hidden_sizes != HIDDEN_SIZES:
                facts["hidden_sizes"] = list(hidden_sizes)
            npz = run_dir / NPZ_FILE
            critic = critic_from_npz(npz, result["activation"], hidden_sizes) if npz.exists() else None
            yield from networks_of(f"{runs_dir.name}/{run_dir.name}", facts, load_policy({**result, "dir": run_dir}), critic)


def original_entries():
    """The original experiment's published networks, as controls."""
    for game in REFERENCE_NETWORKS:
        record, npz = reference_record(game), reference_npz(game)
        activation = record["training_config"]["ACTIVATION"]
        facts = {"game": game, "activation": activation, "seed": record["seed"],
                 "total_steps": record["env_steps"], "eval_mean": record["final_performance"]["sample"]["mean_return"],
                 "learning_rate": record["training_config"]["LR"]}
        yield from networks_of(f"{ORIGINAL_SOURCE}/{game}", facts, policy_from_reference_npz(npz, activation),
                               critic_from_npz(npz, activation))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs_dirs", nargs="*", help=f"run folders to include (default: every {RUNS_DIR.name}* folder)")
    args = parser.parse_args()
    runs_dirs = [PROJECT_DIR / name for name in args.runs_dirs] or sorted(PROJECT_DIR.glob(f"{RUNS_DIR.name}*"))

    key = json.loads(ANSWER_KEY.read_text()) if ANSWER_KEY.exists() else {}
    id_of_source = {entry["source"]: blind_id for blind_id, entry in key.items()}
    BLIND_DIR.mkdir(exist_ok=True)
    added = 0
    for source, text, facts in [*run_entries(runs_dirs), *original_entries()]:
        blind_id = id_of_source.get(source)
        if blind_id is None:
            blind_id = secrets.token_hex(ID_BYTES)
            while blind_id in key:
                blind_id = secrets.token_hex(ID_BYTES)
            added += 1
        (BLIND_DIR / blind_file_name(blind_id)).write_text(text)
        key[blind_id] = {"file": blind_file_name(blind_id), "source": source, **facts,
                         "sha256": hashlib.sha256(text.encode()).hexdigest()}

    ANSWER_KEY.parent.mkdir(exist_ok=True)
    ANSWER_KEY.write_text(json.dumps(dict(sorted(key.items())), indent=1) + "\n")
    print(f"{len(key)} networks in {BLIND_DIR} ({added} new). Answer key: {ANSWER_KEY}")


if __name__ == "__main__":
    main()
