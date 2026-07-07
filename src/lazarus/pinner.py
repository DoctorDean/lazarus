"""Commit-era dependency pinning.

The single biggest reason a stale repo won't even *install* is that ``pip``
now resolves its unpinned (or loosely pinned) dependencies to versions that
did not exist when the repo last worked -- versions that dropped Python 3.6
support, changed APIs, or pulled in an incompatible transitive graph.

Lazarus reconstructs the dependency universe *as it was* on the repo's last
commit date: for each requirement, pick the newest release that existed on
PyPI on or before that date. This is deterministic, needs no execution of the
repo, and is fully general across repos.

The network-free core is :func:`select_version`, which is what the tests
exercise. :func:`fetch_release_history` wraps the PyPI JSON API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Iterable, Optional

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"


@dataclass(frozen=True)
class ReleaseInfo:
    """One released version of a package and when it first appeared."""

    version: str
    uploaded: datetime  # earliest file upload time for the release, in UTC
    yanked: bool = False


def as_cutoff(when: date | datetime) -> datetime:
    """Normalise a date/datetime to an inclusive UTC cutoff instant.

    A bare ``date`` becomes end-of-day UTC so that a release published on the
    commit date itself still counts as "on or before" the cutoff.
    """
    if isinstance(when, datetime):
        dt = when
    else:
        dt = datetime.combine(when, time(23, 59, 59))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_upload_time(files: list[dict]) -> Optional[datetime]:
    """Earliest upload time across a release's distribution files (UTC)."""
    times: list[datetime] = []
    for f in files:
        raw = f.get("upload_time_iso_8601") or f.get("upload_time")
        if not raw:
            continue
        raw = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        times.append(dt.astimezone(timezone.utc))
    return min(times) if times else None


def fetch_release_history(package: str, *, timeout: float = 15.0) -> list[ReleaseInfo]:
    """Fetch every released version of ``package`` from the PyPI JSON API.

    Releases with no uploaded files (a common PyPI artefact) are skipped.
    Raises ``LookupError`` if the package does not exist on PyPI.
    """
    url = PYPI_JSON_URL.format(package=package)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise LookupError(f"package not found on PyPI: {package!r}") from exc
        raise

    out: list[ReleaseInfo] = []
    for version, files in (data.get("releases") or {}).items():
        if not files:
            continue
        uploaded = _parse_upload_time(files)
        if uploaded is None:
            continue
        yanked = all(bool(f.get("yanked")) for f in files)
        out.append(ReleaseInfo(version=version, uploaded=uploaded, yanked=yanked))
    return out


def select_version(
    releases: Iterable[ReleaseInfo],
    cutoff: date | datetime,
    *,
    allow_prerelease: bool = False,
    allow_yanked: bool = False,
) -> Optional[str]:
    """Newest release at or before ``cutoff``. Pure, network-free.

    PEP 440 ordering is used, so ``1.10`` correctly outranks ``1.9``. Returns
    ``None`` when no eligible release exists (e.g. the package is newer than
    the repo, or every candidate was a prerelease/yank that was filtered out).
    """
    cutoff_dt = as_cutoff(cutoff)
    best_ver: Optional[Version] = None
    best_raw: Optional[str] = None
    for r in releases:
        if r.uploaded > cutoff_dt:
            continue
        if r.yanked and not allow_yanked:
            continue
        try:
            v = Version(r.version)
        except InvalidVersion:
            continue
        if v.is_prerelease and not allow_prerelease:
            continue
        if best_ver is None or v > best_ver:
            best_ver, best_raw = v, r.version
    return best_raw


def _requirement_name(requirement: str) -> str:
    """Extract the distribution name from a requirement string.

    Falls back to a permissive split when the string is not a valid PEP 508
    requirement (e.g. it carries an environment marker we don't care about).
    """
    try:
        return Requirement(requirement).name
    except InvalidRequirement:
        for sep in ("[", ";", "=", "<", ">", "!", "~", " "):
            requirement = requirement.split(sep, 1)[0]
        return requirement.strip()


def pin_package(
    package: str,
    cutoff: date | datetime,
    *,
    allow_prerelease: bool = False,
    **fetch_kwargs,
) -> Optional[str]:
    """Resolve a single package to its commit-era version (or ``None``)."""
    history = fetch_release_history(package, **fetch_kwargs)
    return select_version(history, cutoff, allow_prerelease=allow_prerelease)


def pin_requirements(
    requirements: Iterable[str],
    cutoff: date | datetime,
    *,
    allow_prerelease: bool = False,
) -> dict[str, Optional[str]]:
    """Pin each requirement to its commit-era version.

    Returns an ordered mapping of ``name -> version`` (``None`` if nothing
    qualified). Unknown packages are recorded as ``None`` rather than raising,
    so one missing dependency doesn't sink the whole resolution.
    """
    result: dict[str, Optional[str]] = {}
    for requirement in requirements:
        name = _requirement_name(requirement)
        if not name or name in result:
            continue
        try:
            result[name] = pin_package(
                name, cutoff, allow_prerelease=allow_prerelease
            )
        except LookupError:
            result[name] = None
    return result
