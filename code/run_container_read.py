"""The bookkeeping for reads made through Claude Code in Docker containers. Started by docker/reads.sh, which
is run from git-bash and does the launching itself (docker/docker-run.sh):

    bash docker/reads.sh <effort> <repeats> <seconds between starts> <blind id> [<blind id> ...]
    python run_container_read.py show --files <blind ids> --effort <effort> --repeats 3    # lists them; sends nothing

<repeats> is the number of finished reads wanted per file; reads already saved count, so a batch that was
interrupted, or had failures, is finished by running the same command again.

To stop a batch, create the file readings/STOP. Reads already in their containers finish and are saved; the
ones not yet started are dropped, with one line saying how many. Delete the file before the next batch.

The prompt is the same text the API reads are sent (prompts/<prompt>.txt, a blank line, the blind file), piped
into `claude -p` on standard input. The container sees two things only: a work folder holding AGENTS.md (the
one-line instruction) and Claude Code's scratch config folder. No weights file is on its disk, every tool is
switched off, and it never sees this repo. Claude Code adds its own system prompt around the prompt; the saved
transcript shows exactly what.

Saved as readings/<blind id>/<model>_<effort>_container_<prompt>_<n>.txt (the reply) and a folder of that name:
    prompt.txt          the text piped in
    events.jsonl        everything Claude Code printed: the stream of events as they happened
    transcript.jsonl    the session transcript Claude Code wrote in its config folder
    record.json         settings, hashes, times, the image, token counts, the runner's commit
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from layout import CODE_DIR as PROJECT_DIR, WEIGHTS_DIR as BLIND_DIR, reply_path
from readings import DELIVERIES, FILE_PATTERN, READINGS_DIR
from run_reads import (DEFAULT_MODEL, DEFAULT_PROMPT, EFFORTS, FAILED, FINISHED, MAX_TOKENS, NEWLINE, NORMAL, PROMPT_JOIN,
                       PROMPTS_DIR, RECORD_FILE, STATUS, WEIGHTS_HEADING,
                       cell_reads, committed_text, effort_label, model_label, prompt_text, runner_commit, sha256, utc_now,
                       write_json)

PASTED, FROM_FILE = "container", "containerfile"  # the weights pasted in the prompt, or in a file it reads
WEIGHTS_FILE = "weights.txt"  # the name the file-version prompts give
FILE_PROMPT_SUFFIX = "-file"  # prompts/<prompt>-file.txt is the wording that points at the file
INSTRUCTIONS = PROJECT_DIR / "docker" / "AGENTS.md"  # copied into the work folder; Claude Code loads it by itself
PROMPT_FILE, EVENTS_FILE, TRANSCRIPT_FILE, ERRORS_FILE = "prompt.txt", "events.jsonl", "transcript.jsonl", "stderr.txt"
OUTPUT_CAP_VARIABLE = "CLAUDE_CODE_MAX_OUTPUT_TOKENS"  # Claude Code's own output limit per reply, thinking included.
# Left unset, Claude Code picks a default per model, which is below the model's limit for some (64,000 for Opus
# 4.6). Every read sets it; Claude Code lowers a value above a model's limit to that limit.
OUTPUT_CAP_USED = r'"max_tokens":\s*(\d+)'  # the limit Claude Code put in its requests, as its transcript records it.
# (The result event's "maxOutputTokens" is not it: that stays at Claude Code's own figure for the model whatever is set.)
RESUMED_MARK = "Output token limit hit"  # opens the message Claude Code sends itself to continue a cut-off reply
RESULT_EVENT = "result"  # the last event `claude -p --output-format stream-json` prints
STOP_FILE = READINGS_DIR / "STOP"  # create it to stop a batch: reads in flight finish, the rest are not started
TAB = chr(31)  # separates fields in the lines `prepare` prints for reads.sh: the unit separator, which no
# path or argument contains and which, unlike a real tab, bash does not swallow around an empty argument
assert PASTED in DELIVERIES and FROM_FILE in DELIVERIES


def claude_arguments(model: str, effort: str, delivery: str = PASTED) -> list:
    """`claude` in print mode, reading the prompt from standard input, with no connectors, and no tools: except,
    for the file delivery, the file reader and nothing else."""
    tools = ["--tools", "Read", "--allowedTools", "Read"] if delivery == FROM_FILE else ["--tools", ""]
    return ["-p", "--model", model, "--effort", effort, *tools, "--strict-mcp-config",
            "--output-format", "stream-json", "--verbose"]


def sent(blind_id: str, prompt: str, delivery: str):
    """(the text piped in as the prompt, the contents of the weights file in the work folder or None)."""
    if delivery == PASTED:
        return prompt_text(blind_id, prompt), None
    whole = prompt_text(blind_id, prompt)  # the pasted prompt: the wording, then what goes under it
    wording = committed_text(PROMPTS_DIR / f"{prompt}.txt")
    below = whole[len(wording):].lstrip(NEWLINE)
    heading = wording[wording.rindex(WEIGHTS_HEADING):] + PROMPT_JOIN if WEIGHTS_HEADING in wording else ""
    return committed_text(PROMPTS_DIR / f"{prompt}{FILE_PROMPT_SUFFIX}.txt"), heading + below


def planned(args) -> list:
    """(blind id, read name) for every read still to make, numbered after the ones already there."""
    reads = []
    for blind_id in args.files:
        if not (BLIND_DIR / f"{blind_id}.txt").exists():
            sys.exit(f"not in {BLIND_DIR.name}/: {blind_id}")
        label = effort_label(args.effort, max_tokens=args.max_tokens)  # a limit other than the default is in the name
        used, finished = cell_reads(blind_id, args.model, label, args.prompt, args.delivery)
        n = max(used, default=0)
        for _ in range(max(args.repeats - finished, 0)):
            n += 1
            reads.append((blind_id, f"{model_label(args.model)}_{label}_{args.delivery}_{args.prompt}_{n}"))
    return reads


def prepare(args, show_only=False):
    """List the reads still to make. Unless only showing, make each one's folder, prompt file, starting record
    and work folder, and print what reads.sh needs: the stop file's path, the output limit as VARIABLE=value, a line of claude
    arguments joined by a separator, then one line per read holding its folder and its work folder, joined the same way."""
    arguments = claude_arguments(args.model, args.effort, args.delivery)
    reads = planned(args)
    instructions = committed_text(INSTRUCTIONS)
    for line in (f"{len(reads)} container reads to make",
                 f"  {OUTPUT_CAP_VARIABLE}={args.max_tokens} claude "
                 f"{' '.join(repr(a) if a == '' else a for a in arguments)}   (prompt on standard input)",
                 f"  work folder holds only {INSTRUCTIONS.name}: {instructions.strip()!r}"):
        print(line, file=sys.stderr)
    for blind_id, stem in reads:
        prompt, in_file = sent(blind_id, args.prompt, args.delivery)
        print(f"  {blind_id}  {stem}  begins: {prompt[:124]!r}"
              + (f"; {WEIGHTS_FILE} begins: {in_file[:60]!r}" if in_file else ""), file=sys.stderr)
    if show_only or not reads:
        return
    if STOP_FILE.exists():
        sys.exit(f"not starting: {STOP_FILE} exists. Delete it to make these reads.")
    commit = runner_commit()
    print(STOP_FILE.as_posix())
    print(f"{OUTPUT_CAP_VARIABLE}={args.max_tokens}")
    print(TAB.join(arguments))
    for blind_id, stem in reads:
        prompt, in_file = sent(blind_id, args.prompt, args.delivery)
        folder = READINGS_DIR / blind_id / stem
        folder.mkdir(parents=True)
        (folder / PROMPT_FILE).write_bytes(prompt.encode("utf-8"))
        work = Path(tempfile.mkdtemp(prefix="mlp-read-work-"))
        shutil.copyfile(INSTRUCTIONS, work / INSTRUCTIONS.name)
        if in_file is not None:
            (work / WEIGHTS_FILE).write_bytes(in_file.encode("utf-8"))
            (folder / WEIGHTS_FILE).write_bytes(in_file.encode("utf-8"))  # kept: exactly what the reader could open
        write_json(folder / RECORD_FILE, {
            "blind_id": blind_id, "blind_file_sha256": sha256(committed_text(BLIND_DIR / f"{blind_id}.txt")),
            "prompt": args.prompt, "prompt_sha256": sha256(prompt), "delivery": args.delivery,
            "weights_file": WEIGHTS_FILE if in_file is not None else None,
            "weights_file_sha256": sha256(in_file) if in_file is not None else None,
            "harness": "Claude Code, non-interactive, in a Docker container (docker/docker-run.sh)",
            "claude_arguments": arguments, "model_requested": args.model, "effort": args.effort,
            "max_output_tokens_requested": args.max_tokens,
            "tools": "the file reader only" if in_file is not None else "none", "instructions_file": INSTRUCTIONS.name, "instructions_sha256": sha256(instructions),
            "sign_in": "subscription token (claude setup-token), decrypted on the host and passed as an environment variable",
            "runner": "docker/reads.sh", "runner_commit": commit, "prepared_utc": utc_now(),
        })
        print(f"{folder.as_posix()}{TAB}{work.as_posix()}")  # forward slashes, for bash


def discard(lines):
    """Drop prepared reads that were never started (a batch stopped through STOP_FILE): each line is what
    `prepare` printed for one read. A read that has been sent is left alone."""
    for line in lines:
        folder, work = (Path(part) for part in line.strip().split(TAB))
        if (folder / EVENTS_FILE).exists():
            sys.exit(f"not dropping {folder}: it was started")
        shutil.rmtree(folder)
        shutil.rmtree(work, ignore_errors=True)


def output_cap_facts(folder: Path, signed_in: bool) -> dict:
    """From a read's saved events and transcript: how often Claude Code continued a reply that hit the output
    limit, whether the read is a normal one (one reply, not continued), and the limit its requests carried."""
    events = [json.loads(line) for line in (folder / EVENTS_FILE).read_text(encoding="utf-8").splitlines() if line.startswith("{")]
    resumed = sum(e.get("type") == "user" and RESUMED_MARK in json.dumps(e.get("message")) for e in events)
    transcript = folder / TRANSCRIPT_FILE
    used = re.findall(OUTPUT_CAP_USED, transcript.read_text(encoding="utf-8", errors="replace")) if transcript.exists() else []
    return {"resumed_after_output_cap": resumed, NORMAL: signed_in and not resumed,
            "max_output_tokens_used": sorted({int(n) for n in used})}


def backfill():
    """Add the output-limit facts to finished container reads saved before they were recorded."""
    for path in sorted(READINGS_DIR.glob(f"*/*_{PASTED}*_*/{RECORD_FILE}")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get(STATUS) == FINISHED:
            facts = output_cap_facts(path.parent, signed_in=True)
            if any(record.get(key) != value for key, value in facts.items()):
                write_json(path, {**record, **facts})
                print(f"  {path.parent.parent.name} {path.parent.name}: {facts}")


def finish(args):
    """After the container has exited: save the reply, the transcript and the rest of the record."""
    folder = Path(args.folder)
    record = json.loads((folder / RECORD_FILE).read_text(encoding="utf-8"))
    events = [line for line in (folder / EVENTS_FILE).read_text(encoding="utf-8", errors="replace").splitlines()
              if line.startswith("{")]
    (folder / EVENTS_FILE).write_text("\n".join(events) + "\n", encoding="utf-8")
    parsed = [json.loads(line) for line in events]
    result = next((e for e in reversed(parsed) if e.get("type") == RESULT_EVENT), None)
    start = datetime.fromisoformat(args.started_utc)
    record.update({"started_utc": args.started_utc, "finished_utc": utc_now(), "exit_code": args.exit_code,
                   "image": args.image,
                   "image_id": subprocess.run(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"],
                                              capture_output=True, text=True).stdout.strip()})
    record["seconds"] = round((datetime.fromisoformat(record["finished_utc"]) - start).total_seconds())
    signed_in = result is not None and not result.get("is_error")
    if result is not None:
        record.update({key: result.get(key) for key in (
            "subtype", "is_error", "stop_reason", "num_turns", "session_id", "duration_ms", "duration_api_ms",
            "total_cost_usd", "usage", "modelUsage")})
        transcript = Path(args.runtime) / "projects" / "-work" / f"{result.get('session_id')}.jsonl"
        if transcript.exists():
            shutil.copyfile(transcript, folder / TRANSCRIPT_FILE)
        record["transcript_saved"] = transcript.exists()
    record.update(output_cap_facts(folder, signed_in))
    if signed_in:
        reply_path(folder).write_text(result.get("result") or "", encoding="utf-8")
        record[STATUS] = FINISHED
    else:
        errors = (folder / ERRORS_FILE).read_text(encoding="utf-8", errors="replace") if (folder / ERRORS_FILE).exists() else ""
        record.update({STATUS: FAILED, "error": ((result or {}).get("result") or errors)[-2000:]})
    write_json(folder / RECORD_FILE, record)
    shutil.rmtree(args.work, ignore_errors=True)
    print(f"  {record[STATUS]:<8} {record['blind_id']} {folder.name} in {record['seconds']} s, exit code {args.exit_code}"
          + (f", {result.get('num_turns')} turn(s), models {list(result.get('modelUsage') or {})}" if result else "")
          + (f", RESUMED x{record['resumed_after_output_cap']} after the output limit" if record["resumed_after_output_cap"] else "")
          + (f": {record['error'][:200]}" if record[STATUS] == FAILED else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "show"):
        sub = commands.add_parser(name)
        sub.add_argument("--files", nargs="+", required=True, metavar="BLIND_ID")
        sub.add_argument("--model", default=DEFAULT_MODEL)
        sub.add_argument("--effort", choices=EFFORTS, required=True)
        sub.add_argument("--repeats", type=int, default=3, help="finished reads wanted per file")
        sub.add_argument("--delivery", choices=(PASTED, FROM_FILE), default=PASTED)
        sub.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help="output limit per reply, thinking included")
        sub.add_argument("--prompt", choices=sorted(p.stem for p in PROMPTS_DIR.glob("*.txt")), default=DEFAULT_PROMPT)
    sub = commands.add_parser("finish")
    for name in ("folder", "work", "runtime", "image", "started_utc"):
        sub.add_argument(name)
    sub.add_argument("exit_code", type=int)
    commands.add_parser("discard", help="drop the never-started reads listed on standard input")
    commands.add_parser("backfill", help="add the output-limit facts to reads saved before they were recorded")
    args = parser.parse_args()
    if args.command == "finish":
        finish(args)
    elif args.command == "backfill":
        backfill()
    elif args.command == "discard":
        discard(line for line in sys.stdin if line.strip())
    else:
        prepare(args, show_only=args.command == "show")


if __name__ == "__main__":
    main()
