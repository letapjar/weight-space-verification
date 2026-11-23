#!/bin/bash
# Reads through Claude Code in containers, several side by side. Run from git-bash, in this repo:
#
#   bash docker/reads.sh <effort> <repeats> <seconds between starts> <blind id> [<blind id> ...]
#   MODEL=<model id> PROMPT=<label> DELIVERY=containerfile MAX_TOKENS=<n> bash docker/reads.sh ...   # other than the defaults
#
# Every read in the batch is started, <seconds between starts> apart, and they all run together: a container
# waiting on a reply costs nothing, and no route limits requests in flight (notes/rate_limits_2026-11-22.md).
# The gap is there because a burst of starts within a second can be refused. MAX_IN_FLIGHT (default 16) only
# bounds how many containers this laptop holds at once.
#
# To stop a batch, create the file readings/STOP: reads already in their containers finish and are saved, the
# rest are not started. Delete the file before the next batch.
#
# <repeats> is the number of finished reads wanted per file; reads already saved count, so running the same
# command again makes only what is missing or failed.
#
# run_container_read.py lists the reads, prepares each one's prompt and record, and saves the results. This
# script does the launching, through docker/docker-run.sh (the DPAPI token, the mounts). Each container gets its
# own scratch config folder, so reads running side by side share nothing. The prompt goes in on standard input;
# everything Claude Code prints comes back into the read's folder.
set -eu
cd "$(dirname "$0")/.."
source docker/config.sh   # IMAGE, CFG_DIR

PYTHON=.venv/Scripts/python
EFFORT="$1"; REPEATS="$2"; START_GAP="$3"; shift 3
MAX_IN_FLIGHT="${MAX_IN_FLIGHT:-16}"
OPTIONS=(--files "$@" --effort "$EFFORT" --repeats "$REPEATS")
[[ -n "${MODEL:-}" ]] && OPTIONS+=(--model "$MODEL")
[[ -n "${PROMPT:-}" ]] && OPTIONS+=(--prompt "$PROMPT")
[[ -n "${DELIVERY:-}" ]] && OPTIONS+=(--delivery "$DELIVERY")   # container (pasted) or containerfile
[[ -n "${MAX_TOKENS:-}" ]] && OPTIONS+=(--max-tokens "$MAX_TOKENS")   # Claude Code's output limit per reply

# Every read is prepared before any is launched, so each has its number before another could take it.
mapfile -t PREPARED < <("$PYTHON" run_container_read.py prepare "${OPTIONS[@]}" | tr -d '\r')
[[ ${#PREPARED[@]} -eq 0 ]] && exit 0   # nothing to make, or the stop file exists (prepare has said which)
STOP_FILE="${PREPARED[0]}"
OUTPUT_LIMIT="${PREPARED[1]}"   # NAME=value, set in the container
IFS=$'\x1f' read -r -a CLAUDE_ARGS <<< "${PREPARED[2]}"
READS=("${PREPARED[@]:3}")

one_read() {
  local folder="$1" work="$2"
  local name; name="$(basename "$(dirname "$folder")")-$(basename "$folder")"   # <blind id>-<read name>
  local started; started="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
  local status=0
  RUNTIME_NAME="$name" SETTINGS="$OUTPUT_LIMIT" bash docker/docker-run.sh "$work" "${CLAUDE_ARGS[@]}" \
    < "$folder/prompt.txt" > "$folder/events.jsonl" 2> "$folder/stderr.txt" || status=$?
  "$PYTHON" run_container_read.py finish "$folder" "$work" "$CFG_DIR/runtime/$name" "$IMAGE" "$started" "$status"
  rm -rf "${CFG_DIR:?}/runtime/$name"   # its transcript is saved; nothing else in it is kept
}

for i in "${!READS[@]}"; do
  IFS=$'\x1f' read -r folder work <<< "${READS[i]}"
  (( i > 0 )) && sleep "$START_GAP"
  while (( $(jobs -rp | wc -l) >= MAX_IN_FLIGHT )); do wait -n || true; done
  if [[ -e "$STOP_FILE" ]]; then
    printf '%s\n' "${READS[@]:i}" | "$PYTHON" run_container_read.py discard
    echo "  stopped  $STOP_FILE exists: $(( ${#READS[@]} - i )) prepared read(s) not started; waiting for the ones in flight"
    break
  fi
  echo "  start    $(basename "$(dirname "$folder")") $(basename "$folder")"
  one_read "$folder" "$work" &
done
wait
