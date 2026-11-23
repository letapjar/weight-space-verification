# The image the container sign-in notes specify, unchanged: a non-root user, Claude Code from
# npm, and the config folder at the path the launcher mounts the runtime folder on.
# Built and started by docker/docker-run.sh.
FROM node:24-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends git bash ca-certificates procps \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force
USER node
WORKDIR /work
ENV CLAUDE_CONFIG_DIR=/home/node/.claude
