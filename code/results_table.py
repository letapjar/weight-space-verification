"""The results as tables: for every reader, prompt and form of the networks, how many answers named the game.

    python results_table.py            # prints the tables and writes scoring/results.md and scoring/results.csv

One row per (reader, effort, route, prompt, form of the networks). A read is counted if it finished and was a
normal read (run_reads.countable): one reply, not cut off, not refused, not continued by Claude Code. The rule is
the one fixed in scoring/preregistration_2026-11-20_haiku_effort.md: the answer line (Game, Played or Task)
names the network's game and no other of the four. "First" is the secondary count, the right game named first.
Where a network has several countable reads, all are counted, and "networks" says how many networks they cover.

Only prompts with an answer line are tabled. The forms are told from the answer key: which run folder a network
came from.
"""
import csv
import json
from collections import defaultdict

from blind import ANSWER_KEY, PROJECT_DIR
from readings import (BOX_CORRECT, FILE_PATTERN, GAME_KEYWORDS, GAMES_PLAYED, READINGS_DIR, first_game_named,
                      game_line_box, true_games)
from run_reads import RECORD_FILE, STATUS, FINISHED, countable

GAMES = tuple(GAME_KEYWORDS)  # breakout, pong, pacman, freeway
# The forms of the networks, by the start of the run folder each came from, in the order they are tabled.
FORMS = (
    ("upright (200M steps)", ("runs_jax_single_c256_lr_0.005",)),
    ("upright (1B steps)", ("runs_jax_snapshots",)),
    ("upright, 500-8-512-5 shape (200M steps)", ("runs_jax_single_h8x512_c256_lr_0.001",)),
    ("upright (MIT's own networks)", ("original",)),
    ("board turned 180", ("runs_rewired_matched_180", "runs_rewired_180/breakout_tanh_seed2")),
    ("board turned 90", ("runs_rewired_matched_90",)),
    ("cells scrambled", ("runs_rewired_scrambled",)),
    ("all 500 inputs shuffled", ("runs_rewired_inputs_shuffled",)),
    ("weights shuffled", ("weights_shuffled/runs_jax_single_c256_lr_0.005",)),
)
# Prompts with an answer line that the rule can be applied to, in the order they are tabled.
PROMPTS = ("mitfull", "mitfull8x512", "mitcells", "mitunordered", "parkweights", "parkweights8x512")
ROUTES = {"paste": "API", "container": "Claude Code in a container"}
READERS = ("gpt-6-astra", "gpt-6.1-terra", "gpt-6-luna", "opus-5.5", "opus-4.6-1m", "sonnet-5.5", "haiku-5.5")
EFFORTS = ("low", "medium", "high", "xhigh", "xhigh-verbosity-high", "max", "max-cap-64000")
RESULTS_MD, RESULTS_CSV = PROJECT_DIR / "scoring" / "results.md", PROJECT_DIR / "scoring" / "results.csv"
COLUMNS = ("reader", "effort", "route", "prompt", "networks_form", "networks", "reads_counted", *GAMES, "correct",
           "right_game_first", "reads_not_counted", *(f"{game}_first" for game in GAMES))


def form_of(network: dict):
    if network.get(GAMES_PLAYED) or network["network"] != "actor" or network.get("activation") != "tanh":
        return None  # trained on several games, a value network, or a ReLU network: not in these tables
    return next((name for name, starts in FORMS if network["source"].startswith(starts)), None)


def rows() -> list:
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    cells = defaultdict(lambda: {"networks": set(), "games": defaultdict(lambda: [0, 0]), "first": 0, "not_counted": 0,
                                 "games_first": defaultdict(int)})
    for record_path in READINGS_DIR.glob(f"*/*/{RECORD_FILE}"):
        name = FILE_PATTERN.fullmatch(record_path.parent.name + ".txt")
        blind_id = record_path.parent.parent.name
        form = form_of(key[blind_id]) if blind_id in key else None
        if name is None or form is None or name["prompt"] not in PROMPTS or name["delivery"] not in ROUTES:
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get(STATUS) != FINISHED:
            continue  # a request that failed before any response: it was made again
        cell = cells[(name["model"], name["effort"], ROUTES[name["delivery"]], name["prompt"], form)]
        if not countable(record):
            cell["not_counted"] += 1
            continue
        game = true_games(key[blind_id])[0]
        reply = (record_path.parent.parent / f"{record_path.parent.name}.txt").read_text(encoding="utf-8")
        correct = game_line_box(reply, game)[0] == BOX_CORRECT
        cell["networks"].add(blind_id)
        cell["games"][game][0] += correct
        cell["games"][game][1] += 1
        cell["first"] += first_game_named(reply) == game
        cell["games_first"][game] += first_game_named(reply) == game
    order = lambda k: (READERS.index(k[0]) if k[0] in READERS else len(READERS), EFFORTS.index(k[1]) if k[1] in EFFORTS else len(EFFORTS),
                       k[2], PROMPTS.index(k[3]), [name for name, _ in FORMS].index(k[4]))
    table = []
    for cell_key in sorted(cells, key=order):
        cell = cells[cell_key]
        counted = sum(n for _, n in cell["games"].values())
        table.append(dict(zip(COLUMNS, (
            *cell_key, len(cell["networks"]), counted,
            *(f"{cell['games'][game][0]}/{cell['games'][game][1]}" if cell["games"][game][1] else "" for game in GAMES),
            f"{sum(c for c, _ in cell['games'].values())}/{counted}", f"{cell['first']}/{counted}", cell["not_counted"],
            *(f"{cell['games_first'][game]}/{cell['games'][game][1]}" if cell["games"][game][1] else "" for game in GAMES)))))
    return table


def main():
    table = rows()
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, COLUMNS)
        writer.writeheader()
        writer.writerows(table)
    header = "| " + " | ".join(COLUMNS).replace("_", " ") + " |"
    lines = ["# Results", "", __doc__.split("\n\n")[2].replace("\n", " "), "",
             header, "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(str(row[column]) for column in COLUMNS) + " |" for row in table]
    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in table:
        print(f"{row['reader']:<14}{row['effort']:<8}{row['route'][:10]:<11}{row['prompt']:<13}{row['networks_form']:<30}"
              f"{row['correct']:>6}  first {row['right_game_first']:>6}  " + " ".join(f"{game[:4]} {row[game]:<4}" for game in GAMES)
              + (f"  not counted {row['reads_not_counted']}" if row["reads_not_counted"] else ""))
    print(f"wrote {RESULTS_MD.relative_to(PROJECT_DIR)} and {RESULTS_CSV.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
