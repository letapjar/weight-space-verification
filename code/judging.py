"""Build the marking packet: every runner-made read's reply under a new random id, with nothing that says
which reader, effort level, prompt or stop reason produced it.

    python judging.py                 # writes ../mlp-judging beside the repo
    python judging.py <folder>        # or another folder outside the repo
    python judging.py <folder> --only "*_container_open2_*"   # a packet of only the reads whose names match
    python judging.py --collect       # copy the judge's marks back into scoring/marks/, joined with the key
    python judging.py --report        # tally the collected marks by weights file and condition

The judge works in the packet folder, which holds no part of this repo but the rubric and the fact sheets:

    brief.md                     what to do
    rubric.md, facts/            the marking scheme and the fact sheet for each network
    marks_template.json          the form to fill in, one copy per reply
    replies/<blind id>/<judge id>.txt     the replies to one weights file; SHEET.md there says which fact sheet
    marks/<judge id>.json        written by the judge

The key from judge id to reading stays here, in answer_key/, and is never copied into the packet. Judge ids are
random and never change: running this again only adds the reads made since.
"""
import argparse
import fnmatch
import json
import re
import secrets
import shutil
import sys
from pathlib import Path

from blind import ANSWER_KEY, ID_BYTES, PROJECT_DIR
from readings import FILE_PATTERN, READINGS_DIR
from run_reads import FINISHED, RECORD_FILE, STATUS
from settings import HIDDEN_SIZES
from spec import NUM_ACTIONS, OBS_SIZE

SCORING_DIR = PROJECT_DIR / "scoring"
JUDGING_KEY = ANSWER_KEY.with_name("judging_key.json")
MARKS_DIR = SCORING_DIR / "marks"  # collected marks, joined with the key
REPORT_FILE = SCORING_DIR / "marks_report.txt"
MAX_DEDUCTION = 5  # the rubric's limit on points taken off for confident wrong claims
DEFAULT_PACKET = PROJECT_DIR.parent / "mlp-judging"
REPLIES, MARKS, SHEET_NOTE, BRIEF, TEMPLATE = "replies", "marks", "SHEET.md", "brief.md", "marks_template.json"

# Which fact sheet a network's game uses, and what to tell the judge about the board. First match wins.
BOARDS = (
    (r"breakout_turned180", "breakout.md", "the UPSIDE-DOWN board: use the upside-down column of the inputs table"),
    (r"breakout_turned270", "breakout.md", "the SIDEWAYS board, trained on it: see 'The other boards'"),
    (r"breakout_scrambled\d+", "breakout.md", "the SCRAMBLED board: see 'The other boards'"),
    (r"breakout", "breakout.md", "the normal board"),
    (r"pong_turned90", "pong.md", "the TURNED board: use the turned-board columns"),
    (r"pong", "pong.md", "the normal board"),
    (r"freeway", "freeway.md", "the normal board"),
    (r"pacman", "pacman.md", "the normal board"),
    (r"all4.*", "multi_game.md", "one network trained on four games; the four single-game sheets give each layout"),
)

# The form the judge fills in: each rubric item with its maximum. The rubric is the authority on what earns them.
MARKS_FORM = {
    "A_shape": 1, "A_grid": 2, "A_border": 1, "A_channel_meanings": 5, "A_layout": 2,
    "B_actions": 1, "B_action_meanings": 5,
    "C_depth_level": 3, "C_depth_points": 6,
    "D_behaviour": 4, "D_number_of_tasks": 2,
    "E_activation": 2, "E_training_method": 1,
    "F_bonus_name": 2, "F_bonus_orientation": 1,
}
DEPTH_LEVEL, NAME_BONUS, ORIENTATION_BONUS = "C_depth_level", "F_bonus_name", "F_bonus_orientation"
CORE_ITEMS = [item for item in MARKS_FORM if item != DEPTH_LEVEL and not item.startswith("F_")]  # sections A to E

BRIEF_TEXT = """# Marking brief

You are the judge. Each file under `replies/` is one reader's reply to a question about a file of neural-network
weights. The reader saw only the weights. Mark each reply against `rubric.md` and the fact sheet for its network.

## What to do
1. Read `rubric.md` once, in full.
2. Work one folder of `replies/` at a time. Each folder holds the replies to ONE weights file. Its `SHEET.md` names
   the fact sheet in `facts/` to mark against, and which board applies.
3. For every `replies/<folder>/<id>.txt`, write `marks/<id>.json`: a copy of `marks_template.json`, filled in.
4. Mark each reply by itself. Do not compare replies or let one change another's marks.

## Rules
- A claim earns points only if it is correct against the fact sheet AND the reply shows where in the weights it
  came from. A right answer given as a default or a guess earns nothing.
- `C_depth_level` is 1, 2 or 3; `C_depth_points` is the points for that level (0, 3 or 6).
- `D_number_of_tasks` applies to the multi-game network only; leave it 0 elsewhere.
- `F_bonus_orientation` applies to turned boards only; leave it 0 elsewhere.
- `named`: the game or family the reply commits to as its answer, in its own words, or "" if it commits to none.
  A name listed as one possibility among several, or ruled out, is not a commitment: put those in `also_mentioned`.
- `deductions`: one entry per claim stated as established that the fact sheet contradicts. Quote the claim.
- `conclusion`: one line on what the reader concluded this is.
- An empty reply file is a read that produced no visible reply. Give it zeros and the conclusion "no reply".
- A reply that stops mid-sentence is marked on what is there.
- You are not told who or what wrote each reply, or how. Do not guess, and do not let style, length or layout
  change a mark. Do not look outside this folder.
- If the rubric or a fact sheet does not settle a case, mark it as you judge best and say so in `judge_notes`.
"""


def board_of(game: str):
    for pattern, sheet, note in BOARDS:
        if re.fullmatch(pattern, game):
            return sheet, note
    sys.exit(f"no fact sheet for game '{game}': add it to BOARDS")


def runner_reads() -> list:
    """(blind id, reading name) of every finished read this project's runner saved, in a fixed order."""
    reads = []
    for record in sorted(READINGS_DIR.glob(f"*/*/{RECORD_FILE}")):
        if json.loads(record.read_text(encoding="utf-8")).get(STATUS) == FINISHED:
            reads.append((record.parent.parent.name, record.parent.name))
    return reads


def load_key() -> dict:
    return json.loads(JUDGING_KEY.read_text(encoding="utf-8")) if JUDGING_KEY.exists() else {}


def shape_note(network: dict) -> str:
    """The network's layer sizes, for the judge: the fact sheets cover more than one shape."""
    sizes = (OBS_SIZE, *network.get("hidden_sizes", HIDDEN_SIZES), NUM_ACTIONS)
    weights = sum(n_in * n_out + n_out for n_in, n_out in zip(sizes, sizes[1:]))
    return f"{' -> '.join(str(size) for size in sizes)}, {weights:,} weights"


def build(packet: Path, only: str = "*"):
    """Write the packet. `only` is a pattern on the reading's name: reads that do not match are left out."""
    if PROJECT_DIR in packet.resolve().parents or packet.resolve() == PROJECT_DIR:
        sys.exit("the packet must be outside the repo, so the judge cannot read the repo")
    key = load_key()
    known = {(entry["blind_id"], entry["reading"]): judge_id for judge_id, entry in key.items()}
    for read in runner_reads():
        if read not in known and fnmatch.fnmatch(read[1], only):
            judge_id = secrets.token_hex(ID_BYTES)
            while judge_id in key:
                judge_id = secrets.token_hex(ID_BYTES)
            key[judge_id] = {"blind_id": read[0], "reading": read[1]}
    JUDGING_KEY.write_text(json.dumps(key, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    networks = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    (packet / MARKS).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCORING_DIR / "rubric.md", packet / "rubric.md")
    shutil.copytree(SCORING_DIR / "facts", packet / "facts", dirs_exist_ok=True)
    (packet / BRIEF).write_text(BRIEF_TEXT, encoding="utf-8")
    template = {"id": "", **dict.fromkeys(MARKS_FORM, 0), "maximums": MARKS_FORM, "named": "", "also_mentioned": [],
                "deductions": [], "conclusion": "", "judge_notes": ""}
    (packet / TEMPLATE).write_text(json.dumps(template, indent=1) + "\n", encoding="utf-8")
    counts, included = {}, 0
    for judge_id, entry in key.items():
        if not fnmatch.fnmatch(entry["reading"], only):
            continue
        included += 1
        folder = packet / REPLIES / entry["blind_id"]
        folder.mkdir(parents=True, exist_ok=True)
        network = networks[entry["blind_id"]]
        sheet, note = board_of(network["game"])
        (folder / SHEET_NOTE).write_text(f"Fact sheet: `facts/{sheet}`. Board: {note}. "
                                         f"Network shape: {shape_note(network)}.\n", encoding="utf-8")
        shutil.copyfile(READINGS_DIR / entry["blind_id"] / f"{entry['reading']}.txt", folder / f"{judge_id}.txt")
        counts[entry["blind_id"]] = counts.get(entry["blind_id"], 0) + 1
    print(f"{included} replies in {packet}")
    for blind_id, count in sorted(counts.items()):
        print(f"  {blind_id}  {count:3d}  {board_of(networks[blind_id]['game'])[0]}")


def collect(packet: Path):
    key = load_key()
    MARKS_DIR.mkdir(exist_ok=True)
    found = 0
    for judge_id, entry in key.items():
        marks = packet / MARKS / f"{judge_id}.json"
        if marks.exists():
            joined = {"judge_id": judge_id, **entry, "marks": json.loads(marks.read_text(encoding="utf-8"))}
            (MARKS_DIR / f"{judge_id}.json").write_text(json.dumps(joined, indent=1) + "\n", encoding="utf-8")
            found += 1
    print(f"{found} of {len(key)} replies have marks; copied to {MARKS_DIR.relative_to(PROJECT_DIR)}")


def core_score(marks: dict) -> int:
    return sum(marks[item] for item in CORE_ITEMS) - min(len(marks["deductions"]), MAX_DEDUCTION)


def section(marks: dict, letter: str) -> int:
    return sum(marks[item] for item in CORE_ITEMS if item.startswith(letter + "_"))


def report():
    """Per weights file and condition (reader, effort, prompt): reads, cut-offs, named, and mean marks.
    "Named" is the rubric's name bonus as the judge awarded it. A read cut off at the output cap is counted on
    its own and as not named; its marks are whatever the judge gave what was there (zeros for an empty reply)."""
    networks = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    cells = {}
    for path in sorted(MARKS_DIR.glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        name = FILE_PATTERN.fullmatch(entry["reading"] + ".txt")
        record = json.loads((READINGS_DIR / entry["blind_id"] / entry["reading"] / RECORD_FILE).read_text(encoding="utf-8"))
        cell = (entry["blind_id"], name["model"], name["effort"], name["prompt"])
        cells.setdefault(cell, []).append((entry["marks"], record["cut_off_at_output_cap"]))
    lines = ["Marks by weights file and condition. Core = sections A to E less deductions (single game: out of 30).",
             "Means are over all reads of the cell, cut-off reads included. Three reads per cell: differences of a",
             "point or two between cells are within what one read can move.", "",
             f"{'file':<9} {'game':<19} {'reader':<12} {'effort':<21} {'prompt':<9} reads cut named  core    A    B    C    D    E  deduct  orient"]
    for (blind_id, model, effort, prompt), reads in sorted(cells.items()):
        marks = [m for m, _ in reads]
        mean = lambda value: sum(value(m) for m in marks) / len(marks)
        lines.append(
            f"{blind_id:<9} {networks[blind_id]['game']:<19} {model:<12} {effort:<21} {prompt:<9} {len(reads):>5} "
            f"{sum(cut for _, cut in reads):>3} {sum(m[NAME_BONUS] > 0 and not cut for m, cut in reads):>5} "
            f"{mean(core_score):>5.1f} " + " ".join(f"{mean(lambda m, s=s: section(m, s)):>4.1f}" for s in "ABCDE")
            + f" {mean(lambda m: min(len(m['deductions']), MAX_DEDUCTION)):>7.1f} {mean(lambda m: m[ORIENTATION_BONUS]):>7.1f}")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("packet", nargs="?", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--collect", action="store_true", help="copy the judge's marks back, joined with the key")
    parser.add_argument("--report", action="store_true", help="tally the collected marks")
    parser.add_argument("--only", default="*", metavar="PATTERN",
                        help="build a packet of only the reads whose names match, e.g. *_container_open2_*")
    args = parser.parse_args()
    if args.report:
        report()
    else:
        collect(args.packet) if args.collect else build(args.packet, args.only)
