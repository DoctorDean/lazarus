"""Docker-backed sandbox: the execution substrate for the repair loop.

A :class:`Sandbox` is a long-lived container you can repeatedly ``exec`` into,
copy files to and from, and -- crucially -- ``snapshot`` after an expensive
step so a later traceback never forces you to re-pay a 40-minute build.

Local vs. remote is handled by Docker's own transport rather than by us: a
:class:`DockerClient` with ``docker_host=None`` drives the local daemon
(OrbStack on the Mac); with ``docker_host="ssh://dean@100.x.y.z"`` it drives
the A4500 box over Tailscale SSH. Every command is the same ``docker ...``
invocation either way.

The subprocess call is injected (``runner=``) so the whole surface is unit
tested with a fake -- no Docker daemon required.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, Union


def find_docker() -> str:
    """Locate the docker binary, falling back to OrbStack's shim path."""
    exe = shutil.which("docker")
    if exe:
        return exe
    cand = os.path.expanduser("~/.orbstack/bin/docker")
    return cand if os.path.exists(cand) else "docker"

Command = Union[str, Sequence[str]]

# runner(argv, *, input_bytes, timeout, env) -> (exit_code, stdout, stderr)
Runner = Callable[..., "tuple[int, str, str]"]


class DockerError(RuntimeError):
    """Docker is missing, unreachable, or a lifecycle command failed."""


@dataclass
class CommandResult:
    """Outcome of one command, with the fields the repair loop reasons over."""

    command: Command
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    @property
    def combined(self) -> str:
        """stdout then stderr, as an agent would read a failing run."""
        parts = [p for p in (self.stdout, self.stderr) if p]
        return "\n".join(parts)

    def tail(self, lines: int = 40) -> str:
        """Last ``lines`` lines of combined output -- the repair-loop context."""
        return "\n".join(self.combined.splitlines()[-lines:])

    def raise_for_status(self) -> "CommandResult":
        if not self.ok:
            raise DockerError(
                f"command failed (exit {self.exit_code}): {self.command}\n"
                f"{self.tail()}"
            )
        return self


def _subprocess_runner(
    argv: Sequence[str],
    *,
    input_bytes: Optional[bytes] = None,
    timeout: Optional[float] = None,
    env: Optional[dict] = None,
) -> "tuple[int, str, str]":
    """Default runner: shell out to the real ``docker`` binary."""
    merged = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            list(argv),
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
            env=merged,
        )
    except FileNotFoundError as exc:  # docker binary not on PATH
        raise DockerError(
            f"could not find executable {argv[0]!r}; is Docker/OrbStack installed?"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or b""
        err = exc.stderr or b""
        text_err = err.decode("utf-8", "replace")
        return 124, out.decode("utf-8", "replace"), text_err + "\n[timed out]"
    return (
        proc.returncode,
        proc.stdout.decode("utf-8", "replace"),
        proc.stderr.decode("utf-8", "replace"),
    )


class DockerClient:
    """Thin wrapper over the ``docker`` CLI, local or remote (via DOCKER_HOST)."""

    def __init__(
        self,
        *,
        docker_host: Optional[str] = None,
        binary: str = "docker",
        runner: Runner = _subprocess_runner,
    ) -> None:
        self.binary = binary
        self.docker_host = docker_host
        self._runner = runner

    @property
    def _env(self) -> Optional[dict]:
        return {"DOCKER_HOST": self.docker_host} if self.docker_host else None

    def run(
        self,
        args: Sequence[str],
        *,
        input_bytes: Optional[bytes] = None,
        timeout: Optional[float] = None,
    ) -> CommandResult:
        argv = [self.binary, *args]
        start = time.monotonic()
        code, out, err = self._runner(
            argv, input_bytes=input_bytes, timeout=timeout, env=self._env
        )
        return CommandResult(
            command=argv,
            exit_code=code,
            stdout=out,
            stderr=err,
            duration_s=time.monotonic() - start,
        )

    def available(self) -> bool:
        """True if a Docker daemon answers (``docker version`` succeeds)."""
        try:
            return self.run(["version", "--format", "{{.Server.Version}}"]).ok
        except DockerError:
            return False

    def pull(self, image: str, *, platform: str = "linux/amd64",
             timeout: Optional[float] = 1800.0) -> CommandResult:
        return self.run(["pull", "--platform", platform, image], timeout=timeout)


def _new_name(prefix: str = "lazarus") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class Sandbox:
    """A running container: exec into it, move files, snapshot, tear down.

    Use as a context manager so the container is always removed::

        with Sandbox(client, "pablogainza/masif:latest") as box:
            box.exec("cd /masif/data/masif_site && ./predict_site.sh 4ZQK_A")
            box.get("/masif/.../pred_data/4ZQK_A.npy", "out/4ZQK_A.npy")
            box.snapshot("lazarus/masif:site-ready")
    """

    client: DockerClient
    image: str
    name: str = field(default_factory=_new_name)
    workdir: str = "/work"
    platform: str = "linux/amd64"
    keepalive: Sequence[str] = ("sleep", "infinity")
    gpus: Optional[str] = None      # e.g. "all" -> passes GPUs to the container
    started: bool = field(default=False, init=False)

    def start(self, *, timeout: Optional[float] = 300.0) -> "Sandbox":
        if self.started:
            return self
        args = ["run", "-d", "--platform", self.platform, "--name", self.name, "-w", self.workdir]
        if self.gpus:
            args += ["--gpus", self.gpus]
        args += [self.image, *self.keepalive]
        self.client.run(args, timeout=timeout).raise_for_status()
        self.started = True
        return self

    def exec(
        self,
        command: Command,
        *,
        workdir: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> CommandResult:
        """Run a command in the container. Strings run under ``bash -lc``."""
        args = ["exec"]
        if workdir is not None:
            args += ["-w", workdir]
        for key, value in (env or {}).items():
            args += ["-e", f"{key}={value}"]
        args.append(self.name)
        if isinstance(command, str):
            args += ["bash", "-lc", command]
        else:
            args += list(command)
        return self.client.run(args, timeout=timeout)

    def put(self, local_path: str, container_path: str) -> CommandResult:
        return self.client.run(
            ["cp", local_path, f"{self.name}:{container_path}"]
        ).raise_for_status()

    def get(self, container_path: str, local_path: str) -> CommandResult:
        return self.client.run(
            ["cp", f"{self.name}:{container_path}", local_path]
        ).raise_for_status()

    def write_file(self, path: str, content: str) -> CommandResult:
        """Write ``content`` to ``path`` inside the container (for patches)."""
        return self.client.run(
            ["exec", "-i", self.name, "bash", "-c", f"cat > {shlex.quote(path)}"],
            input_bytes=content.encode("utf-8"),
        ).raise_for_status()

    def read_file(self, path: str, *, max_bytes: int = 100_000) -> str:
        """Return the first ``max_bytes`` bytes of a file inside the container."""
        res = self.client.run(
            ["exec", self.name, "bash", "-lc", f"head -c {int(max_bytes)} {shlex.quote(path)}"]
        )
        res.raise_for_status()
        return res.stdout

    def snapshot(self, tag: str, *, message: Optional[str] = None) -> str:
        """``docker commit`` the live container to ``tag``; return the tag.

        This is how Lazarus banks an expensive successful step (a completed
        build, a resolved binary chain) so a later failure re-runs from the
        checkpoint instead of from scratch.
        """
        args = ["commit"]
        if message:
            args += ["-m", message]
        args += [self.name, tag]
        self.client.run(args).raise_for_status()
        return tag

    def stop(self, *, remove: bool = True) -> None:
        if not self.started:
            return
        cmd = ["rm", "-f", self.name] if remove else ["stop", self.name]
        self.client.run(cmd)
        self.started = False

    def __enter__(self) -> "Sandbox":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
