#!/bin/bash
# Build the image and start one Claude Code session in a container, as the container sign-in notes (kept outside this repo) describe.
# Adapted from the launcher those notes come with: the folder (.claude-wsp), the image and the mounts changed.
# Run it from git-bash, in this repo:
#
#   bash docker/docker-run.sh --auth-test                               # expect AUTH OK
#   bash docker/docker-run.sh <work folder> <claude arguments> < prompt # one session, prompt on standard input
#
# Isolation: the container sees ONLY
#   - <work folder>, mounted at /work (nothing for --auth-test). Never this repo.
#   - a scratch Claude config dir at ~/.claude-wsp/runtime, holding onboarding state and the sessions' own
#     transcripts: never your real ~/.claude
#
# Secrets are NOT in that mount. ~/.claude-wsp itself is the host-side store for token.dpapi and is never
# mounted into the container: the token travels as an environment variable, so no secret touches the container
# filesystem at all. The DPAPI-encrypted token is the ONLY sign-in this script uses.
set -eu
cd "$(dirname "$0")/.."

source docker/config.sh   # IMAGE, CFG_DIR (the token store), RUNTIME_DIR

mkdir -p "$CFG_DIR" "$RUNTIME_DIR"

# Auth. The token value is only ever handled inside this script's process and docker: never printed, logged, or
# committed. There is deliberately no plaintext fallback. The block below is that launcher's, with
# the folder changed and its first branch (a CLAUDE_CODE_OAUTH_TOKEN already set in the calling shell) left out:
# here the DPAPI-encrypted token at $CFG_DIR/token.dpapi is the only sign-in. Create it in your own PowerShell
# (paste the token at the hidden prompt):
#   Read-Host -AsSecureString 'setup-token' | ConvertFrom-SecureString |
#     Out-File "$env:USERPROFILE\.claude-wsp\token.dpapi"
# A missing file, or one that does not decrypt, stops the script here before any container starts.
if [[ -s "$CFG_DIR/token.dpapi" ]]; then
  # env -u PSModulePath: keep PS7 module paths from breaking Windows PowerShell 5.1
  TOKEN="$(env -u PSModulePath powershell.exe -NoProfile -Command \
    "\$s = Get-Content \"\$env:USERPROFILE\\.claude-wsp\\token.dpapi\" | ConvertTo-SecureString; \
     [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR(\$s))" \
    | tr -d '[:space:]')" || TOKEN=""
  if [[ -z "$TOKEN" ]]; then
    echo "auth: token.dpapi did not decrypt (new machine or Windows profile?). Re-encrypt it: see the header of docker/docker-run.sh." >&2
    exit 1
  fi
  echo "auth: using DPAPI-encrypted token"
else
  echo "auth: no token. Create $CFG_DIR/token.dpapi: see the header of docker/docker-run.sh." >&2
  exit 1
fi
TOKEN_ARGS=(-e "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN")
unset TOKEN
# SETTINGS: space-separated NAME=value pairs handed to the container as environment variables (reads.sh passes
# Claude Code's output limit this way). Settings only: the token never goes through here.
SETTING_ARGS=()
for setting in ${SETTINGS:-}; do SETTING_ARGS+=(-e "$setting"); done
if [[ ! -f "$RUNTIME_DIR/.claude.json" ]]; then
  printf '{"hasCompletedOnboarding": true}\n' > "$RUNTIME_DIR/.claude.json"
fi
RUNTIME_MOUNT="$(cd "$RUNTIME_DIR" && pwd -W)"

docker build -q -t "$IMAGE" docker/claude-code > /dev/null

# --auth-test: one-shot container that only checks Claude authentication, then exits.
if [[ "${1:-}" == "--auth-test" ]]; then
  MSYS_NO_PATHCONV=1 exec docker run --rm \
    "${TOKEN_ARGS[@]}" \
    -v "$RUNTIME_MOUNT:/home/node/.claude" \
    --entrypoint bash \
    "$IMAGE" -c "claude -p 'Reply with exactly: AUTH OK'"
fi

if [[ $# -lt 2 || ! -d "$1" ]]; then
  echo "usage: bash docker/docker-run.sh --auth-test | <work folder> <claude arguments> < prompt" >&2
  exit 1
fi
WORK_MOUNT="$(cd "$1" && pwd -W)"
shift
# -i: the prompt is piped in on standard input (it is too long for a Windows command line)
MSYS_NO_PATHCONV=1 exec docker run --rm -i \
  "${TOKEN_ARGS[@]}" "${SETTING_ARGS[@]}" \
  -v "$WORK_MOUNT:/work" \
  -v "$RUNTIME_MOUNT:/home/node/.claude" \
  "$IMAGE" claude "$@"
