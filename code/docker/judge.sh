#!/bin/bash
# Start one independent judge: a fresh Claude Code session in a container, signed in with the subscription
# (the DPAPI token, through docker/docker-run.sh; never an API key). The container sees only the marking packet
# (built by judging.py, outside this repo), mounted as its work folder. The judge can read and write files
# there and nothing else: no shell, no web, no connectors, no instructions file, no part of this repo.
# Run from git-bash, in this repo:
#
#   bash docker/judge.sh <packet folder> <name> <replies folder> [<replies folder> ...]
#   JUDGE_MODEL=<model id> bash docker/judge.sh ...      # a judge other than the default
#
# What it prints (its final report) is kept in logs/judge_<name>.log. Its marks go to the packet's marks folder.
set -u
cd "$(dirname "$0")/.."
source docker/config.sh   # CFG_DIR

JUDGE_MODEL="${JUDGE_MODEL:-claude-sonnet-5-5}"
PACKET="$1"; NAME="$2"; shift 2
[[ -f "$PACKET/brief.md" && $# -ge 1 ]] || { echo "usage: bash docker/judge.sh <packet folder> <name> <replies folder> ..." >&2; exit 1; }
FOLDERS="$(printf '%s, ' "$@")"; FOLDERS="${FOLDERS%, }"
mkdir -p logs
LOG="logs/judge_$NAME.log"

PROMPT="Read brief.md in this folder and follow it. \
Mark only the replies in these folders of replies/: $FOLDERS. Leave the other folders alone. \
Further rules. \
(1) Work only from files in this folder. Do not open, search or list anything outside it. \
(2) Do not try to work out who or what wrote a reply, or under what conditions. Mark what it says. \
(3) If the brief, the rubric or a fact sheet is unclear, note it in the marks file and in your final report rather than guessing. \
(4) When done, report how many replies you marked, and every ruling you made where the rubric did not decide."

echo "judge $NAME, model $JUDGE_MODEL, in a container, folders: $*" | tee "$LOG"
set -o pipefail
printf '%s' "$PROMPT" | RUNTIME_NAME="judge-$NAME" bash docker/docker-run.sh "$PACKET" \
  -p --model "$JUDGE_MODEL" --tools "Read,Write,Glob,Grep" --permission-mode acceptEdits --strict-mcp-config \
  2>&1 | tee -a "$LOG"
status=$?
rm -rf "${CFG_DIR:?}/runtime/judge-$NAME"   # the judge's scratch config; its report is in the log
echo "exit $status" | tee -a "$LOG"
# Its tab closes when this script ends. After a failure it waits, so the error stays on screen.
if [[ $status -ne 0 ]]; then read -r -p "The judge failed (see above, and $LOG). Press Enter to close this tab: " _; fi
exit $status
