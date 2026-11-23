"""A marking packet for the weights-shuffled control (the twenty-eighth test), outside this repo.

    .venv/Scripts/python judging_shuffled.py            # build or extend the packet
    .venv/Scripts/python judging_shuffled.py --collect  # copy the marks back and print the table

Every countable reply to a weights-shuffled file goes into one folder under a random id, with nothing saying
which reader wrote it or which network the file was made from. The judge sorts each reply into one of three
classes (the user's scoring, 2026-11-22): declines to name a game; names one while saying the weights do not
support it; names one without saying so. The key from random id to read stays in this repo.
"""
import csv
import json
import re
import secrets
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from blind import ANSWER_KEY, PROJECT_DIR
from experiments.shuffle_weights import SHUFFLED_OF
from readings import FILE_PATTERN, READINGS_DIR
from run_reads import RECORD_FILE, countable

PACKET = PROJECT_DIR.parent / "mlp-judging-shuffled"
FOLDERS = ("a", "b", "c")  # three folders, so three judges can share the marking
KEY = PROJECT_DIR / "answer_key" / "judging_shuffled_key.json"
MARKS_HOME = PROJECT_DIR / "scoring" / "marks_shuffled"
TABLE = PROJECT_DIR / "scoring" / "weights_shuffled.csv"  # one row per reader, read by post_figures.py
PROMPT = "mitfull"
DECLINES, RECOGNISES, GUESSES = "declines", "names_with_recognition", "names_without_recognition"
CLASSES = (DECLINES, RECOGNISES, GUESSES)
TEMPLATE = {"class": "", "game_named": "", "says_weights_scrambled_or_structureless": False, "stated_confidence": "",
            "quote": "", "judge_notes": ""}

BRIEF = f"""# Marking brief

You are the judge. Each file in `replies/<folder>/` is one reader's reply. The reader was given a description of a
10 x 10 grid game setup and the weights of a small neural network, told that the network had been trained to play
a game on that grid, and asked which game.

What the reader was not told: in every case here the weights had been shuffled. Every number in the file had been
moved to a random place within its own matrix, so the weights encode no game. There is no right game to name.
The right reading is to recognise that the weights do not identify a game.

## What to do
For every `replies/<folder>/<id>.txt`, write `marks/<id>.json`: a copy of `marks_template.json`, filled in.
Mark each reply by itself.

## The three classes (`class`)
- `{DECLINES}`: the reply does not give a game as its answer. It says the game is undetermined, cannot be
  identified, or is not supported by the weights. It may list possibilities, but it does not pick one.
- `{RECOGNISES}`: the reply gives a game or a best guess as its answer, AND says that the weights do not
  support the identification: for example that the weights do not actually identify the game, that they show no
  structure, or that they look scrambled, shuffled, random, noise-like or untrained. The reader names something
  because it was asked to, and says so.
- `{GUESSES}`: the reply gives a game as its answer and does not say that the weights fail to support it.
  A low confidence figure, or words like "likely", "probably" or "best guess" by themselves, are not enough: the
  reply must say that the weights do not identify or support the answer, or that they lack structure. A reply that
  argues its answer from patterns it claims to see in the weights belongs here even if it is hesitant.

## The other fields
- `game_named`: the game or family given as the answer, in the reply's own words, or "" for `{DECLINES}`.
- `says_weights_scrambled_or_structureless`: true if the reply says, anywhere, that the weights look scrambled,
  shuffled, randomised, noise-like, untrained, or without spatial or positional structure. Otherwise false.
- `stated_confidence`: the confidence the reply states, as written (for example "15%"), or "".
- `quote`: the sentence from the reply that best supports the class you chose, word for word.
- `judge_notes`: anything you were unsure of.

## Rules
- You are not told who or what wrote each reply. Do not guess, and do not let style, length or layout change a
  mark. Do not look outside this folder.
- If a reply does not fit a class cleanly, choose the closest, and say why in `judge_notes`.
- There is no `rubric.md` and there are no fact sheets for this packet; this brief is the whole rule.
"""


def shuffled_reads():
    """(blind id, read name) for every countable reply to a weights-shuffled file under the MIT prompt."""
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    for blind_id, network in sorted(key.items()):
        if SHUFFLED_OF not in network:
            continue
        for record_path in sorted((READINGS_DIR / blind_id).glob(f"*/{RECORD_FILE}")):
            name = FILE_PATTERN.fullmatch(record_path.parent.name + ".txt")
            if name and name["prompt"] == PROMPT and countable(json.loads(record_path.read_text(encoding="utf-8"))):
                yield blind_id, record_path.parent.name


def build():
    key = json.loads(KEY.read_text(encoding="utf-8")) if KEY.exists() else {}
    known = {(entry["blind_id"], entry["read"]): judge_id for judge_id, entry in key.items()}
    for folder in FOLDERS:
        (PACKET / "replies" / folder).mkdir(parents=True, exist_ok=True)
    (PACKET / "marks").mkdir(exist_ok=True)
    (PACKET / "brief.md").write_text(BRIEF, encoding="utf-8")
    (PACKET / "marks_template.json").write_text(json.dumps(TEMPLATE, indent=1) + "\n", encoding="utf-8")
    added = 0
    for blind_id, read in shuffled_reads():
        judge_id = known.get((blind_id, read))
        if judge_id is None:
            judge_id = secrets.token_hex(4)
            while judge_id in key:
                judge_id = secrets.token_hex(4)
            key[judge_id] = {"blind_id": blind_id, "read": read}
            added += 1
        reply = (READINGS_DIR / blind_id / f"{read}.txt").read_text(encoding="utf-8")
        folder = FOLDERS[int(judge_id, 16) % len(FOLDERS)]
        (PACKET / "replies" / folder / f"{judge_id}.txt").write_text(reply, encoding="utf-8")
    KEY.write_text(json.dumps(dict(sorted(key.items())), indent=1) + "\n", encoding="utf-8")
    print(f"{len(key)} replies in {PACKET} ({added} new); key in {KEY.relative_to(PROJECT_DIR)}")


def collect():
    key = json.loads(KEY.read_text(encoding="utf-8"))
    MARKS_HOME.mkdir(parents=True, exist_ok=True)
    by_reader, scrambled, missing = defaultdict(Counter), Counter(), 0
    for judge_id, entry in key.items():
        source = PACKET / "marks" / f"{judge_id}.json"
        if not source.exists():
            missing += 1
            continue
        shutil.copy(source, MARKS_HOME / source.name)
        mark = json.loads(source.read_text(encoding="utf-8"))
        reader = re.match(r"(.+?)_(low|medium|high|xhigh|max)", entry["read"]).group(1)
        by_reader[reader][mark["class"]] += 1
        scrambled[reader] += bool(mark["says_weights_scrambled_or_structureless"])
    print(f"{'reader':<16}{'reads':>6}{'declines':>10}{'names, recognises':>19}{'names, no recognition':>23}{'correct read':>14}{'says scrambled':>16}")
    for reader, classes in sorted(by_reader.items()):
        reads = sum(classes.values())
        print(f"{reader:<16}{reads:>6}{classes[DECLINES]:>10}{classes[RECOGNISES]:>19}{classes[GUESSES]:>23}"
              f"{classes[DECLINES] + classes[RECOGNISES]:>11} of {reads:<2}{scrambled[reader]:>13}")
    if missing:
        print(f"{missing} replies not marked yet")
    with TABLE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("reader", "reads", *CLASSES, "correct_read", "says_scrambled"))
        for reader, classes in sorted(by_reader.items()):
            writer.writerow((reader, sum(classes.values()), *(classes[name] for name in CLASSES),
                             classes[DECLINES] + classes[RECOGNISES], scrambled[reader]))


if __name__ == "__main__":
    collect() if "--collect" in sys.argv else build()
