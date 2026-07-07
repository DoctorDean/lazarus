"""Lazarus — turn dead research code into a callable pipeline component.

Lazarus clones a stale repo, reads its paper for intent, and runs a
build -> execute -> read-traceback -> repair loop in a sandbox. It pins
dependencies to the repo's commit era, resolves external-binary chains,
locates the real capability buried in the scripts, and emits a fixed
integration contract: an importable module, a CLI, a pinned container, and
a smoke test that proves the method runs on a fresh input.
"""

__version__ = "0.0.1"

from lazarus.pinner import (
    ReleaseInfo,
    fetch_release_history,
    pin_package,
    pin_requirements,
    select_version,
)
from lazarus.sandbox import (
    CommandResult,
    DockerClient,
    DockerError,
    Sandbox,
)
from lazarus.contract import (
    Contract,
    IOSpec,
    SmokeCheck,
    emit,
)

__all__ = [
    "__version__",
    # pinner
    "ReleaseInfo",
    "fetch_release_history",
    "pin_package",
    "pin_requirements",
    "select_version",
    # sandbox
    "CommandResult",
    "DockerClient",
    "DockerError",
    "Sandbox",
]
