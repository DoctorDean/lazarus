# The reference submission: Lazarus behind the SUBMISSION.md contract.
#
# It drives *other* containers to do the revival, so it needs a Docker socket — either the
# host's, or a DOCKER_HOST pointing at a remote builder:
#
#   docker build -t lazarus-submission:0.5 benchmark/reference
#   docker run --rm \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -e ANTHROPIC_API_KEY \
#     -v <staged>:/task:ro -v <out>:/out \
#     lazarus-submission:0.5 \
#       --repo-url https://github.com/owner/repo --commit <sha> \
#       --task /task/task.yaml --out /out
#
# Mounting the host socket gives this container control of the daemon. That is a real
# privilege, and it is why an *untrusted* submission should get a remote DOCKER_HOST
# pointed at a disposable builder instead. The reference submission is ours, so the socket
# is acceptable here; SUBMISSION.md does not ask third parties to need it.
FROM python:3.12-slim

# docker-cli, NOT docker.io: this container talks to a daemon it does not own, over the
# socket. Debian trixie splits the two, and docker.io is the *daemon* — asking for it with
# --no-install-recommends yields a dockerd we never run and no `docker` binary at all,
# which builds green and fails at run time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates docker-cli \
    && rm -rf /var/lib/apt/lists/* \
    && docker --version

# The resurrection loop drives the Claude CLI.
RUN curl -fsSL https://claude.ai/install.sh | bash || \
    echo "install the claude CLI at build time or mount it at /usr/local/bin/claude"
ENV PATH="/root/.local/bin:${PATH}"

# The SDK drives the CLI with --dangerously-skip-permissions (permission_mode=
# "bypassPermissions" in lazarus.scout and lazarus.resurrect), and the CLI refuses that flag
# as root: "cannot be used with root/sudo privileges for security reasons". That killed the
# Scout two seconds into the first real end-to-end run. IS_SANDBOX is the documented escape
# for an already-isolated container, and here the container *is* the isolation boundary. The
# alternative — a non-root user — would have to match the host's docker group id to keep the
# mounted socket usable, which does not port between hosts. Note this failure is not
# architecture-specific: it would have happened identically on x86.
ENV IS_SANDBOX=1

WORKDIR /app
# lazarus-bio provides the pinner, sandbox, scout and resurrection loop.
RUN pip install --no-cache-dir "lazarus-bio[agent]>=0.5" pyyaml

COPY lazarus_submission.py /app/lazarus_submission.py

ENTRYPOINT ["python", "/app/lazarus_submission.py"]
