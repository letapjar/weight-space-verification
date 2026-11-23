# Names shared by docker-run.sh and read.sh. Sourced, not run.
IMAGE="mlp-claude-code"
HOST_HOME="${USERPROFILE:-$HOME}"
CFG_DIR="$HOST_HOME/.claude-wsp"            # secrets: host only, never mounted
# The container's /home/node/.claude: the scratch folder, or a subfolder of it when RUNTIME_NAME is set, so that
# containers running side by side each have their own and share no session files.
RUNTIME_DIR="$CFG_DIR/runtime${RUNTIME_NAME:+/$RUNTIME_NAME}"
