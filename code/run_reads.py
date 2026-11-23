"""Send blind weight files to a model and save everything about each read.

    python run_reads.py --files 01a9fefe 2db098c5 --efforts high --repeats 3 --dry-run
    python run_reads.py --files 01a9fefe 2db098c5 --efforts high --repeats 3 --model gpt-6-astra

The strict test: one new conversation per read, no system prompt, no tools, one user message made of the
wording in prompts/<prompt>.txt, a blank line, and the blind file. The reader never sees anything else.
The provider is chosen by the model's name (PROVIDERS); every provider gets the same prompt, byte for byte.

Each read is one request and is never retried. Whatever its stop reason, it is saved as

    readings/<blind id>/<model>_<effort>_<delivery>_<prompt>_<n>.txt     the visible reply, nothing added
    readings/<blind id>/<model>_<effort>_<delivery>_<prompt>_<n>/
        request.json            the request exactly as sent (the key is in a header and is never saved)
        response.json           the whole response as the API returned it
        thinking_summary.txt    the model's own summary of its thinking, where it gave one
        record.json             ids, times, token counts, stop reason, block types, hashes, the runner's commit

A request that fails before a response arrives leaves only record.json with the error, and does not count.
--repeats is the number of finished reads wanted per file and effort; reads this runner already saved count,
so a batch that was interrupted is finished by running the same command again.

The API key is read from the provider's environment variable in the process that starts this script.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from layout import CODE_DIR as PROJECT_DIR, PROMPTS_DIR, WEIGHTS_DIR as BLIND_DIR, reply_path
from readings import DELIVERIES, FILE_PATTERN, PROMPTS, READINGS_DIR

DEFAULT_MODEL = "claude-opus-5-5"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
VERBOSITIES = ("low", "medium", "high")  # how long the visible reply is; a setting only some providers have
MAX_TOKENS = 128_000  # the default output cap: the most every model used so far allows, thinking included
REQUEST_TIMEOUT_SECONDS = 3600.0
# Pacing (notes/rate_limits_2026-11-22.md): the limits are per minute, not on requests in flight, so a batch is
# started a few seconds apart and runs together. A burst within a second can be refused, hence the gap.
START_GAP_SECONDS = 5.0
PARALLEL = 16
RATE_LIMIT_STATUS = 429
RATE_LIMIT_RESENDS = 5  # a rate refusal produced no reply, so sending the same request again is not a retry of a read
DELIVERY = "paste"
DEFAULT_PROMPT = "open2"  # the open question in its corrected wording
FIRST_PROMPT = "open"  # the wording as first typed and first sent; kept so those reads can be rebuilt
PROMPT_JOIN = "\n\n"  # between the wording and the weights
# A prompt that ends with the original experiment's weights heading (the MIT prompt and every variation of it)
# sends the weights under the original's own section headings.
WEIGHTS_HEADING = "THE NETWORK'S WEIGHTS"
DIGITS, NEWLINE, BACKREF_1 = "[0-9]+", chr(10), chr(92) + "1"  # pieces of the patterns in original_layout
REQUEST_FILE, RESPONSE_FILE, THINKING_FILE, RECORD_FILE = (
    "request.json", "response.json", "thinking_summary.txt", "record.json")
STATUS, FINISHED, FAILED = "status", "finished", "failed"
NORMAL = "normal_read"  # in every record: the read ended by itself, in one reply. False for a reply cut off at the
# output cap, and for one Claude Code continued after the cap (the user's ruling: such reads are not counted)


def countable(record: dict) -> bool:
    """Whether a read is counted in results: finished, and a normal read. The rest stay on disk, flagged."""
    return record.get(STATUS) == FINISHED and record[NORMAL]
assert DELIVERY in DELIVERIES and DEFAULT_PROMPT in PROMPTS


class Anthropic:
    name, key_variable, model_prefix = "anthropic", "ANTHROPIC_API_KEY", "claude-"
    endpoint = "POST /v1/messages (streamed)"
    reply_types = ("thinking", "text")  # the only blocks a read without tools should hold
    takes_verbosity = False

    @staticmethod
    def request_body(model: str, effort: str, prompt: str, verbosity=None, max_tokens=MAX_TOKENS) -> dict:
        return {
            "model": model,
            "max_tokens": max_tokens,
            "thinking": {"type": "adaptive", "display": "summarized"},  # the default mode, with its summary returned
            "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": prompt}],
        }

    @staticmethod
    def client():
        import anthropic
        return anthropic.Anthropic(api_key=os.environ[Anthropic.key_variable], max_retries=0,
                                   timeout=REQUEST_TIMEOUT_SECONDS), f"anthropic {anthropic.__version__} (Python)"

    @staticmethod
    def send(client, body: dict):
        """(the response as a plain dict, the request's id, the API version sent)"""
        with client.messages.stream(**body) as stream:
            version = stream.response.request.headers.get("anthropic-version")
            return stream.get_final_message().to_dict(), stream.request_id, version

    @staticmethod
    def parse(message: dict) -> dict:
        blocks = message["content"]
        stop = message["stop_reason"]
        return {
            "reply": "".join(b["text"] for b in blocks if b["type"] == "text"),
            "thinking_summary": "\n\n".join(b["thinking"] for b in blocks if b["type"] == "thinking" and b.get("thinking")),
            "response_id": message["id"], "model_served": message["model"],
            "stop_reason": stop, "stop_details": message.get("stop_details"),
            NORMAL: stop == "end_turn", "cut_off_at_output_cap": stop == "max_tokens",
            "usage": message["usage"], "block_types": [b["type"] for b in blocks],
        }


class OpenAI:
    name, key_variable, model_prefix = "openai", "OPENAI_API_KEY", "gpt-"
    endpoint = "POST /v1/responses (streamed)"
    reply_types = ("reasoning", "message")
    takes_verbosity = True

    @staticmethod
    def request_body(model: str, effort: str, prompt: str, verbosity=None, max_tokens=MAX_TOKENS) -> dict:
        return {
            "model": model,
            "max_output_tokens": max_tokens,
            "reasoning": {"effort": effort, "summary": "auto"},  # the summary is returned, as for the other provider
            **({} if verbosity is None else {"text": {"verbosity": verbosity}}),  # not sent unless asked for
            "input": [{"role": "user", "content": prompt}],
        }

    @staticmethod
    def client():
        import openai
        return openai.OpenAI(api_key=os.environ[OpenAI.key_variable], max_retries=0,
                             timeout=REQUEST_TIMEOUT_SECONDS), f"openai {openai.__version__} (Python)"

    @staticmethod
    def send(client, body: dict):
        raw = client.responses.with_raw_response.create(**body, stream=True)
        final = None
        for event in raw.parse():  # the last event that carries the response is its finished form
            final = getattr(event, "response", final)
        if final is None:
            raise RuntimeError("the stream ended without a response")
        return final.to_dict(), raw.headers.get("x-request-id"), raw.headers.get("openai-version")

    @staticmethod
    def parse(response: dict) -> dict:
        items = response.get("output") or []
        parts = [part for item in items if item["type"] == "message" for part in item.get("content") or []]
        summaries = [s["text"] for item in items if item["type"] == "reasoning" for s in item.get("summary") or []]
        status, incomplete = response["status"], (response.get("incomplete_details") or {}).get("reason")
        refusals = [part["refusal"] for part in parts if part["type"] == "refusal"]
        return {
            "reply": "".join(part["text"] for part in parts if part["type"] == "output_text"),
            "thinking_summary": "\n\n".join(summaries),
            "response_id": response["id"], "model_served": response["model"],
            "stop_reason": status if incomplete is None else f"{status}: {incomplete}",
            "stop_details": {"refusals": refusals, "error": response.get("error")} if refusals or response.get("error") else None,
            NORMAL: status == "completed" and not refusals,
            "cut_off_at_output_cap": incomplete == "max_output_tokens",
            "usage": response.get("usage"), "block_types": [item["type"] for item in items],
        }


PROVIDERS = (Anthropic, OpenAI)


def provider_of(model: str):
    for provider in PROVIDERS:
        if model.startswith(provider.model_prefix):
            return provider
    sys.exit(f"no provider for model '{model}': names start with " + " or ".join(p.model_prefix for p in PROVIDERS))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def committed_text(path) -> str:
    """A text file with the line endings git stores (LF), so the prompt is the same bytes on every machine."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def original_layout(weights: str) -> str:
    """A blind file's text with its section headings reworded as the original experiment wrote them: the last
    layer is called the output layer, and only W1's heading explains its rows. The numbers are untouched."""
    last = max(int(k) for k in re.findall(r"^W(" + DIGITS + r") ", weights, re.MULTILINE))
    weights = re.sub(rf"^(W(?!1 )" + DIGITS + r" [^:]*: one line per row) [^" + NEWLINE + r"]*$", r"" + BACKREF_1,
                     weights, flags=re.MULTILINE)
    return re.sub(rf"^([Wb]{last}) [(]layer {last} ", BACKREF_1 + " (output layer ", weights, flags=re.MULTILINE)


def prompt_text(blind_id: str, prompt: str) -> str:
    weights = committed_text(BLIND_DIR / f"{blind_id}.txt")
    wording = committed_text(PROMPTS_DIR / f"{prompt}.txt")
    if WEIGHTS_HEADING in wording:
        weights = original_layout(weights)
    return wording + PROMPT_JOIN + weights


def model_label(model: str) -> str:
    """The model's name as file names write it: claude-opus-5-5 -> opus-5.5 (no underscores, see readings.py);
    Claude Code's long-context form claude-opus-4-6[1m] -> opus-4.6-1m (no brackets in a folder name)."""
    name = model.removeprefix(Anthropic.model_prefix).replace("[", "-").replace("]", "")
    return re.sub(r"(\d)-(\d)", r"\1.\2", name)


def effort_label(effort: str, verbosity=None, max_tokens=MAX_TOKENS) -> str:
    """The effort field of a file name. A read sent with a verbosity setting, or with an output cap other than
    the default, says so there, so reads under different settings never mix."""
    return (effort + ("" if verbosity is None else f"-verbosity-{verbosity}")
            + ("" if max_tokens == MAX_TOKENS else f"-cap-{max_tokens}"))


def cell_reads(blind_id: str, model: str, effort: str, prompt: str, delivery: str = DELIVERY):
    """(numbers already used, how many finished reads a runner saved) for one file, model, effort label, prompt
    and delivery."""
    used, finished = set(), 0
    folder = READINGS_DIR / blind_id
    for path in folder.iterdir() if folder.is_dir() else ():
        match = FILE_PATTERN.fullmatch(path.name if path.is_file() else path.name + ".txt")
        if match is None or (match["model"], match["effort"], match["delivery"], match["prompt"]) != (
                model_label(model), effort, delivery, prompt):
            continue
        used.add(int(match["n"]))
        record = path / RECORD_FILE
        if path.is_dir() and record.exists() and json.loads(record.read_text(encoding="utf-8"))[STATUS] == FINISHED:
            finished += 1
    return used, finished


def plan(blind_ids, model: str, efforts, prompt: str, repeats: int, verbosity=None, max_tokens=MAX_TOKENS) -> list:
    """The reads still to make, each with its number already chosen."""
    reads = []
    for blind_id in blind_ids:
        for effort in efforts:
            used, finished = cell_reads(blind_id, model, effort_label(effort, verbosity, max_tokens), prompt)
            n = max(used, default=0)
            for _ in range(max(repeats - finished, 0)):
                n += 1
                reads.append({"blind_id": blind_id, "model": model, "effort": effort, "verbosity": verbosity,
                              "max_tokens": max_tokens,
                              "prompt": prompt, "n": n})
    return reads


def read_stem(read: dict) -> str:
    label = effort_label(read["effort"], read.get("verbosity"), read.get("max_tokens", MAX_TOKENS))
    return f"{model_label(read['model'])}_{label}_{DELIVERY}_{read['prompt']}_{read['n']}"


def runner_commit() -> str:
    def git(*args):
        return subprocess.run(["git", *args], cwd=PROJECT_DIR, capture_output=True, text=True).stdout.strip()
    return git("rev-parse", "HEAD") + (" plus uncommitted changes" if git("status", "--porcelain", "--untracked-files=no") else "")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def save_response(provider, folder, reply_path, response: dict, record: dict):
    """Write a response's files and fill the record from it. `response` is the API's response as a plain dict."""
    write_json(folder / RESPONSE_FILE, response)
    parsed = provider.parse(response)
    reply, summary = parsed.pop("reply"), parsed.pop("thinking_summary")
    reply_path.write_text(reply, encoding="utf-8")
    if summary:
        (folder / THINKING_FILE).write_text(summary, encoding="utf-8")
    record.update({
        STATUS: FINISHED, **parsed, "thinking_summary_returned": bool(summary),
        "blocks_other_than_reply_and_thinking": [t for t in parsed["block_types"] if t not in provider.reply_types],
    })


def retry_after_seconds(error):
    """The wait a rate refusal asks for, or None when the error is anything else. A refusal for a spend limit or
    an empty balance carries no retry-after, and waiting would not help, so it is not one of these."""
    if getattr(error, "status_code", None) != RATE_LIMIT_STATUS:
        return None
    try:
        return float(error.response.headers["retry-after"])
    except (AttributeError, KeyError, ValueError):
        return None


def send_paced(provider, client, body: dict, record: dict):
    """provider.send, waiting out rate refusals. Each refusal is counted in the record."""
    record["rate_limit_resends"] = 0
    while True:
        try:
            return provider.send(client, body)
        except Exception as error:
            wait = retry_after_seconds(error)
            if wait is None or record["rate_limit_resends"] >= RATE_LIMIT_RESENDS:
                raise
            record["rate_limit_resends"] += 1
            print(f"  rate limit: waiting {wait:.0f} s before sending again", flush=True)
            time.sleep(wait)


def run_read(provider, client, sdk: str, read: dict, commit: str) -> dict:
    stem = read_stem(read)
    folder = READINGS_DIR / read["blind_id"] / stem
    folder.mkdir(parents=True)
    prompt = prompt_text(read["blind_id"], read["prompt"])
    body = provider.request_body(read["model"], read["effort"], prompt, read.get("verbosity"),
                                 read.get("max_tokens", MAX_TOKENS))
    write_json(folder / REQUEST_FILE, body)
    record = {
        "blind_id": read["blind_id"], "blind_file_sha256": sha256(committed_text(BLIND_DIR / f"{read['blind_id']}.txt")),
        "prompt": read["prompt"], "prompt_sha256": sha256(prompt), "delivery": DELIVERY, "n": read["n"],
        "provider": provider.name, "endpoint": provider.endpoint, "model_requested": read["model"],
        "effort": read["effort"], "verbosity": read.get("verbosity"),
        "max_tokens": read.get("max_tokens", MAX_TOKENS),
        "system_prompt": None, "tools_declared": 0, "fallback_model": None, "prior_turns": 0, "retries": 0,
        "sdk": sdk, "runner": "run_reads.py", "runner_commit": commit,
        "started_utc": utc_now(),
    }
    started = time.monotonic()
    print(f"  start   {read['blind_id']} {stem}", flush=True)
    try:
        response, record["request_id"], record["api_version"] = send_paced(provider, client, body, record)
        save_response(provider, folder, reply_path(folder), response, record)
    except Exception as error:  # every failure is recorded; the read does not count and is made again next time
        record.update({STATUS: FAILED, "error": f"{type(error).__name__}: {error}"})
    record["finished_utc"], record["seconds"] = utc_now(), round(time.monotonic() - started)
    write_json(folder / RECORD_FILE, record)
    usage = record.get("usage") or {}
    print(f"  {record[STATUS]:<8}{read['blind_id']} {stem}: " + (
        record["error"] if record[STATUS] == FAILED else
        f"{record['stop_reason']}, {usage.get('input_tokens')} in, {usage.get('output_tokens')} out, "
        f"{record['seconds']} s"), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--files", nargs="+", required=True, metavar="BLIND_ID")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--efforts", nargs="+", choices=EFFORTS, required=True)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help="output cap, thinking included")
    parser.add_argument("--verbosity", choices=VERBOSITIES, help="reply length setting, for providers that have one; "
                        "not sent unless given")
    parser.add_argument("--repeats", type=int, default=3, help="finished reads wanted per file and effort")
    parser.add_argument("--prompt", choices=sorted(p.stem for p in PROMPTS_DIR.glob("*.txt")), default=DEFAULT_PROMPT)
    parser.add_argument("--parallel", type=int, default=PARALLEL, help="most reads in flight at once")
    parser.add_argument("--start-gap", type=float, default=START_GAP_SECONDS, help="seconds between starts")
    parser.add_argument("--dry-run", action="store_true", help="list the reads and send nothing")
    args = parser.parse_args()

    provider = provider_of(args.model)
    if args.verbosity and not provider.takes_verbosity:
        sys.exit(f"{provider.name} has no verbosity setting")
    missing = [blind_id for blind_id in args.files if not (BLIND_DIR / f"{blind_id}.txt").exists()]
    if missing:
        sys.exit(f"not in {BLIND_DIR.name}/: {' '.join(missing)}")
    reads = plan(args.files, args.model, args.efforts, args.prompt, args.repeats, args.verbosity, args.max_tokens)
    print(f"{len(reads)} reads to make: {args.model} ({provider.name}), prompt '{args.prompt}', max_tokens {args.max_tokens}, "
          f"no system prompt, no tools, no fallback, started {args.start_gap:g} s apart, at most {args.parallel} in flight")
    for read in reads:
        print(f"  {read['blind_id']}  {read_stem(read)}  "
              f"({len(prompt_text(read['blind_id'], read['prompt'])):,} characters)")
    if args.dry_run or not reads:
        return
    if not os.environ.get(provider.key_variable):
        sys.exit(f"{provider.key_variable} is not set in this window; nothing was sent")

    client, sdk = provider.client()
    commit = runner_commit()
    with ThreadPoolExecutor(args.parallel) as pool:
        futures = []
        for i, read in enumerate(reads):
            if i:
                time.sleep(args.start_gap)
            futures.append(pool.submit(run_read, provider, client, sdk, read, commit))
        records = [future.result() for future in futures]
    done = [record for record in records if record[STATUS] == FINISHED]
    print(f"\n{len(done)} of {len(records)} finished; "
          f"{sum(not record[NORMAL] for record in done)} of them did not stop normally; "
          f"{sum((r['usage'] or {}).get('input_tokens', 0) for r in done):,} tokens in, "
          f"{sum((r['usage'] or {}).get('output_tokens', 0) for r in done):,} out")
    if len(done) < len(records):
        sys.exit("run the same command again to make the reads that failed")  # a failing exit keeps the tab open


if __name__ == "__main__":
    main()
