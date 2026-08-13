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

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates docker.io \
    && rm -rf /var/lib/apt/lists/*

# The resurrection loop drives the Claude CLI.
RUN curl -fsSL https://claude.ai/install.sh | bash || \
    echo "install the claude CLI at build time or mount it at /usr/local/bin/claude"
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
# lazarus-bio provides the pinner, sandbox, scout and resurrection loop.
RUN pip install --no-cache-dir "lazarus-bio[agent]>=0.5" pyyaml

COPY lazarus_submission.py /app/lazarus_submission.py

ENTRYPOINT ["python", "/app/lazarus_submission.py"]
