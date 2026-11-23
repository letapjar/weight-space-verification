"""Write the public copy of this project: the networks that were read, the prompts, every published read, the
scoring and the code, in a clean folder beside this repo.

    python public_export.py                 # writes ../weight-space-verification (and replaces what this script wrote there before)
    python public_export.py --check         # only search an existing public copy for personal details

What goes in (README_NOTES below is printed into the public README):
    weights/<blind id>.txt                  the policy networks any published read was made of; numbers only
    prompts/<prompt>.txt                    the wording of every published prompt
    reads/<blind id>/<read>/                one folder per read: reply.txt, record.json, and the provider's own
                                            record of the exchange (response.json for an API read,
                                            transcript.jsonl for a Claude Code read), thinking_summary.txt, and
                                            marks.json where a blind judge marked the read
    answer_key/                             what each blind id is, and the judges' fact sheets. Kept apart: give
                                            a reader weights/ only
    scoring/                                the predictions written before each test, the results tables, the
                                            rubric, and the judges' own reports
    figures/                                the heat maps and charts
    code/                                   the programs that made all of the above, as they were run, and the
                                            scores of the mixed networks at play

What stays out: reads made with a prompt in WITHHELD_PROMPTS (the first wordings, since superseded), the
training runs, value networks, and every file that only repeats the prompt (prompt.txt, request.json,
events.jsonl; each record.json holds the hashes of the prompt and of the weights file, and the prompt is
prompts/<prompt>.txt, a blank line, and weights/<blind id>.txt, with MIT's section headings for the MIT prompts).
"""
import argparse
import ast
import json
import re
import shutil
import sys

import numpy as np

from blind import ANSWER_KEY, BLIND_DIR, PROJECT_DIR
from layout import PROMPTS_DIR, reply_path
from original import ACTOR, ACTOR_HEAD, GIF_TRACE_FILE, NPZ_FILE, REFERENCE_DIR, REFERENCE_NETWORKS, layer_names
from readings import FILE_PATTERN, PROMPTS, READINGS_DIR
from run_reads import RECORD_FILE, RESPONSE_FILE, STATUS, FINISHED, THINKING_FILE

PUBLIC_DIR = PROJECT_DIR.parent / "weight-space-verification"
WITHHELD_PROMPTS = ("open", "scaffold")  # the first wordings, superseded on 2026-11-20; not published
TRANSCRIPT_FILE = "transcript.jsonl"
KEPT_FILES = (RECORD_FILE, RESPONSE_FILE, TRANSCRIPT_FILE, THINKING_FILE)
CODE = ("run_reads.py", "run_container_read.py", "readings.py", "results_table.py", "heatmaps.py", "blind.py",
        "spec.py", "public_export.py", "post_figures.py", "haiku_effort_figure.py", "haiku_effort_report.py",
        "judging.py", "judging_shuffled.py", "test_readings.py", "test_heatmaps.py",  # test_run_reads.py needs the unpublished prompts
        "experiments/rotate.py", "experiments/mix_layers.py", "experiments/reverse_blocks.py",
        "experiments/shuffle_weights.py",
        "games.py", "test_games.py", *sorted(f"jaxport/{path.name}" for path in (PROJECT_DIR / "jaxport").glob("*.py")),
        "experiments/play_mixed.py", "experiments/play_mixed_results.txt", "experiments/play_mixed_h8x512_results.txt",
        "experiments/play_swapped_seeds.py", "experiments/play_swapped_seeds_results.txt",
        "experiments/play_turned_pong_over_breakout.py", "experiments/play_turned_pong_over_breakout_results.txt",
        "experiments/play_turned_pong_under_breakout.py", "experiments/play_turned_pong_under_breakout_results.txt",
        "docker/reads.sh", "docker/judge.sh", "docker/docker-run.sh", "docker/config.sh", "docker/AGENTS.md",
        "docker/claude-code/Dockerfile", "layout.py", "experiments/play_npz.py")
# Never exported, whatever imports them: this script's own tests need the unpublished first wording.
NOT_EXPORTED = ("test_run_reads.py",)
# The lines of layout.py that differ in the public copy, where the code sits in code/ and the data folders
# beside it under their public names. Each must occur exactly once in layout.py.
PUBLIC_LAYOUT = (("DATA_DIR = CODE_DIR  ", "DATA_DIR = CODE_DIR.parent  "), ('"blind"', '"weights"'),
                 ('"readings"', '"reads"'), ('"blind_answer_key.json"', '"answer_key.json"'),
                 ("REPLY_INSIDE = None", 'REPLY_INSIDE = "reply.txt"'))
NETWORKS = "networks"  # <blind id>.npz for every file in weights/: the same network as arrays, at full precision
TEXT_TOLERANCE = 6e-4  # the text is rounded to three decimals
FRONT = ("README.md", "LICENSE", "NOTICE.md", "Dockerfile", ".dockerignore", ".gitattributes", "requirements.txt",
         "requirements-jax.txt", "quickstart.ipynb")  # kept in public/, copied to the top of the public copy
SCORING = ("scoring/preregistration_2026-11-20_haiku_effort.md", "scoring/results.md", "scoring/results.csv",
           "scoring/weights_shuffled.csv", "scoring/rubric.md", "scoring/haiku_effort_report.txt",
           "post/main_table.md", "post/haiku_effort_study.md", "post/haiku_effort_study.png")
SCORING_DIR = PROJECT_DIR / "scoring"
# The judges' reports on published reads only: the first day's judging was of reads that are not published.
JUDGE_REPORT_PREFIXES = ("open2_", "hypotheses2_", "shuffled_")
# Where each judging round keeps its marks, and the key from a mark's random id to the read it is of.
MARKS = ((SCORING_DIR / "marks", ANSWER_KEY.parent / "judging_key.json"),
         (SCORING_DIR / "marks_shuffled", ANSWER_KEY.parent / "judging_shuffled_key.json"))
MARKS_FILE = "marks.json"
FIGURES = PROJECT_DIR / "figures" / "post"
README = PROJECT_DIR / "public" / "README.md"  # the public copy's front page, kept here so it is versioned
KEY_FACTS = ("game", "activation", "seed", "total_steps", "eval_mean", "learning_rate", "games", "eval_by_game",
             "turned_degrees", "scrambled_seed", "first_layer_from", "later_layers_from", "derived_from", "source",
             "network", "hidden_sizes", "num_envs", "blocks_reversed_of", "weights_shuffled_of")
# What must not appear anywhere in the public copy: the shapes of an email address, a Windows user folder, and
# account ids and keys, plus the names in PERSONAL_NAMES_FILE (one per line; that file is not tracked by git and
# is not exported, so the names themselves are written nowhere else). A name is matched in lower case,
# Capitalised and UPPER CASE only, so a chance run of mixed-case letters inside an encrypted blob does not match.
PERSONAL_NAMES_FILE = PROJECT_DIR / ".personal_names"
LICENSE = PROJECT_DIR / "public" / "LICENSE"
NOTICE = PROJECT_DIR / "public" / "NOTICE.md"  # whose work everything not under LICENSE is
VENDORED = PROJECT_DIR / "jaxport" / "third_party" / "purejaxrl"
# The author's name is meant to appear in two lines only, which are not searched: the README's byline and the
# licence's copyright line.
# The published repository's own address is meant to appear (the README's Colab link, the notebook's clone).
REPOSITORY = "letapjar/weight-space-verification"
AUTHOR_LINES = {README.name: "Independent Research", LICENSE.name: "Copyright (c)"}
SHAPES = (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", r"[A-Za-z]:[\\/]{1,2}Users", r"/(?:mnt/)?c/Users",
          r"(?<![A-Za-z0-9_+/-])sk-[A-Za-z0-9_-]{20,}", r"(?<![A-Za-z0-9_+/-])proj_[A-Za-z0-9]{8,}",
          r"(?<![A-Za-z0-9_+/-])org-[A-Za-z0-9]{8,}")


def personal_pattern():
    if not PERSONAL_NAMES_FILE.exists():
        sys.exit(f"{PERSONAL_NAMES_FILE.name} is missing: list the names to search for there, one per line")
    names = [line.strip() for line in PERSONAL_NAMES_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    spellings = [re.escape(form) for name in names for form in (name.lower(), name.capitalize(), name.upper())]
    return re.compile("|".join([*spellings, *SHAPES]))


def published_reads():
    """(blind id, read folder) for every finished read whose prompt is published."""
    for record_path in sorted(READINGS_DIR.glob(f"*/*/{RECORD_FILE}")):
        name = FILE_PATTERN.fullmatch(record_path.parent.name + ".txt")
        if name is None or name["prompt"] in WITHHELD_PROMPTS:
            continue
        if json.loads(record_path.read_text(encoding="utf-8")).get(STATUS) == FINISHED:
            yield record_path.parent.parent.name, record_path.parent


def local_imports(path) -> set:
    """The files of this project that a Python file imports, as paths relative to the project."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
        else:
            continue
        for name in names:
            parts = name.split(".")
            for candidate in ("/".join(parts) + ".py", "/".join(parts) + "/__init__.py"):
                if (PROJECT_DIR / candidate).is_file():
                    found.add(candidate)
                    found.update(f"{'/'.join(parts[:i])}/__init__.py" for i in range(1, len(parts))
                                 if (PROJECT_DIR / "/".join(parts[:i]) / "__init__.py").is_file())
    return found


def with_imports(paths) -> list:
    """The given files and every file of this project they import, directly or not: no published script is
    missing a module of ours. Third-party libraries are not files here; they are in the requirements."""
    todo, seen = list(paths), set()
    while todo:
        relative = todo.pop()
        if relative in seen or relative in NOT_EXPORTED:
            continue
        seen.add(relative)
        if relative.endswith(".py"):
            todo.extend(local_imports(PROJECT_DIR / relative))
    return sorted(seen)


def public_layout() -> str:
    text = (PROJECT_DIR / "layout.py").read_text(encoding="utf-8")
    for private, public in PUBLIC_LAYOUT:
        if text.count(private) != 1:
            sys.exit(f"layout.py: expected exactly one {private!r}")
        text = text.replace(private, public)
    return text


def text_arrays(text: str) -> dict:
    """A weights file's numbers as arrays, named as the network files name them (actor/<layer>/kernel, .../bias)."""
    blocks, current = {}, None
    for line in text.splitlines():
        heading = re.match(r"([Wb])(\d+) ", line)
        if heading:
            current = blocks.setdefault((heading[1], int(heading[2])), [])
        elif line.strip() and current is not None:
            current.append([float(value) for value in line.split()])
    names = layer_names(ACTOR_HEAD, max(number for _, number in blocks) - 1)
    return {f"{ACTOR}/{names[number - 1]}/{'kernel' if kind == 'W' else 'bias'}":
            np.array(rows if kind == "W" else rows[0], dtype=np.float32) for (kind, number), rows in blocks.items()}


def network_file(entry: dict):
    """The saved arrays a blind file was written from, or None where it only ever existed as text. A file with
    its blocks in reverse order ("#...") is the same network as its source."""
    source = entry["source"].split("#")[0]
    if source.startswith("original/"):
        game = source.split("/")[1]
        return REFERENCE_DIR / game / f"{REFERENCE_NETWORKS[game]}.npz"
    path = PROJECT_DIR / source / NPZ_FILE
    return path if path.is_file() else None


def export_network(blind_id: str, entry: dict, out) -> str:
    """Write networks/<blind id>.npz and return how it was made. Stops if the arrays and the text disagree."""
    from_text = text_arrays((BLIND_DIR / f"{blind_id}.txt").read_text(encoding="utf-8"))
    path = network_file(entry)
    if path is None:
        np.savez(out, **from_text)
        return "from the text (this network only ever existed as text)"
    saved = np.load(path)
    for name, values in from_text.items():
        if saved[name].shape != values.shape or not np.allclose(saved[name], values, atol=TEXT_TOLERANCE):
            sys.exit(f"{blind_id}: {path} does not match weights text at {name}")
    shutil.copyfile(path, out)
    return "the saved arrays, full precision"


def marks_by_read() -> dict:
    """(blind id, read name) -> the file holding a blind judge's marks for that read."""
    found = {}
    for folder, key_path in MARKS:
        for mark_id, read in json.loads(key_path.read_text(encoding="utf-8")).items():
            path = folder / f"{mark_id}.json"
            if path.exists():
                found[read["blind_id"], read.get("reading") or read["read"]] = path
    return found


def export():
    if PUBLIC_DIR.exists():
        for name in ("weights", NETWORKS, "prompts", "reads", "answer_key", "scoring", "figures", "code"):
            shutil.rmtree(PUBLIC_DIR / name, ignore_errors=True)
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    reads, marks = list(published_reads()), marks_by_read()
    blind_ids, prompts = sorted({blind_id for blind_id, _ in reads}), set()
    for blind_id, folder in reads:
        out = PUBLIC_DIR / "reads" / blind_id / folder.name
        out.mkdir(parents=True)
        reply = reply_path(folder)
        shutil.copyfile(reply, out / "reply.txt") if reply.exists() else (out / "reply.txt").write_text("", encoding="utf-8")
        for name in KEPT_FILES:
            if (folder / name).exists():
                shutil.copyfile(folder / name, out / name)
        if (blind_id, folder.name) in marks:
            shutil.copyfile(marks[blind_id, folder.name], out / MARKS_FILE)
        prompts.add(FILE_PATTERN.fullmatch(folder.name + ".txt")["prompt"])
    (PUBLIC_DIR / "weights").mkdir(parents=True)
    (PUBLIC_DIR / NETWORKS).mkdir()
    made = {}
    for blind_id in blind_ids:
        shutil.copyfile(BLIND_DIR / f"{blind_id}.txt", PUBLIC_DIR / "weights" / f"{blind_id}.txt")
        made[blind_id] = export_network(blind_id, key[blind_id], PUBLIC_DIR / NETWORKS / f"{blind_id}.npz")
    (PUBLIC_DIR / NETWORKS / "how_made.json").write_text(json.dumps(made, indent=1) + "\n", encoding="utf-8")
    (PUBLIC_DIR / "prompts").mkdir()
    for prompt in sorted(prompts):
        for path in PROMPTS_DIR.glob(f"{prompt}*.txt"):  # the prompt, and its file-delivery wording where there is one
            if path.stem in (prompt, f"{prompt}-file"):
                shutil.copyfile(path, PUBLIC_DIR / "prompts" / path.name)
    (PUBLIC_DIR / "answer_key").mkdir()
    (PUBLIC_DIR / "answer_key" / "answer_key.json").write_text(json.dumps(
        {blind_id: {fact: key[blind_id][fact] for fact in KEY_FACTS if fact in key[blind_id]} for blind_id in blind_ids},
        indent=1) + "\n", encoding="utf-8")
    (PUBLIC_DIR / "answer_key" / "prompts.json").write_text(json.dumps(
        {prompt: PROMPTS[prompt] for prompt in sorted(prompts)}, indent=1) + "\n", encoding="utf-8")
    for group, paths in (("scoring", SCORING), ("code", with_imports(CODE))):
        for relative in paths:
            target = PUBLIC_DIR / group / (relative.rsplit("/", 1)[1] if group == "scoring" else relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT_DIR / relative, target)
    shutil.copytree(SCORING_DIR / "facts", PUBLIC_DIR / "answer_key" / "facts")
    (PUBLIC_DIR / "scoring" / "judge_reports").mkdir()
    for report in sorted((SCORING_DIR / "judge_reports").glob("*.md")):
        if report.name.startswith(JUDGE_REPORT_PREFIXES):
            shutil.copyfile(report, PUBLIC_DIR / "scoring" / "judge_reports" / report.name)
    shutil.copytree(FIGURES, PUBLIC_DIR / "figures")
    (PUBLIC_DIR / "code" / "layout.py").write_text(public_layout(), encoding="utf-8", newline="\n")
    for game, network in REFERENCE_NETWORKS.items():  # the original's networks and records, where original.py looks
        (PUBLIC_DIR / "code" / REFERENCE_DIR.name / game).mkdir(parents=True)
        for name in (f"{network}.npz", f"{network}.json", GIF_TRACE_FILE):
            shutil.copyfile(REFERENCE_DIR / game / name, PUBLIC_DIR / "code" / REFERENCE_DIR.name / game / name)
    for name in FRONT:
        shutil.copyfile(README.parent / name, PUBLIC_DIR / name)
    vendored = PUBLIC_DIR / "code" / VENDORED.relative_to(PROJECT_DIR)
    vendored.mkdir(parents=True)
    for path in VENDORED.iterdir():  # the unmodified third-party files with their own licence (see NOTICE)
        if path.is_file():
            shutil.copyfile(path, vendored / path.name)
    print(f"wrote {PUBLIC_DIR}: {len(reads)} reads of {len(blind_ids)} networks under {len(prompts)} prompts")


def check() -> int:
    """Print every place the public copy holds something that looks personal. Returns how many files matched."""
    matched, personal = 0, personal_pattern()
    for path in sorted(p for p in PUBLIC_DIR.rglob("*") if p.is_file() and ".git" not in p.parts):
        if path.suffix == ".png":
            continue
        text = path.read_text(encoding="utf-8", errors="replace").replace(REPOSITORY, "")
        if path.parent == PUBLIC_DIR and path.name in AUTHOR_LINES:
            text = "\n".join(line for line in text.splitlines() if AUTHOR_LINES[path.name] not in line)
        hits = sorted({match.group(0) for match in personal.finditer(text)})
        if hits:
            matched += 1
            print(f"  {path.relative_to(PUBLIC_DIR)}: {hits[:6]}")
    print(f"{matched} file(s) in {PUBLIC_DIR.name} match the personal-details patterns")
    return matched


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only search the existing public copy")
    args = parser.parse_args()
    if not args.check:
        export()
    sys.exit(1 if check() else 0)


if __name__ == "__main__":
    main()
