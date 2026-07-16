"""The Lazarus registry — a living archive of resurrected tools.

Every resurrection already emits a :class:`~lazarus.contract.Contract` and a
reproduction certificate. The *registry* is the public index over those: one
:class:`RegistryEntry` per revived tool, capturing where it came from, what it
does, how it was proven, and how to pull it — so a revived brick is discoverable
and fetchable, not just sitting in one person's repo.

This is deliberately a thin data layer:
- entries live as YAML under ``registry/entries/`` (the source of truth that the
  benchmark and, later, the ``@lazarus revive`` bot append to);
- ``registry/index.json`` is the aggregated, fetchable artifact;
- the catalog can be loaded from a local directory **or** a remote URL, so a
  ``pip install lazarus-bio`` user can browse and ``lazarus pull`` without cloning.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml

# Canonical published location (live once `next` is merged to main).
RAW_BASE = "https://raw.githubusercontent.com/DoctorDean/lazarus/main"
DEFAULT_INDEX_URL = f"{RAW_BASE}/registry/index.json"

# Files that make up a contract bundle, fetched by ``lazarus pull``.
CONTRACT_FILES = ("lazarus.yaml", "predict.py", "Dockerfile", "smoke_test.py", "REPRODUCE.md")


@dataclass
class RegistryEntry:
    name: str                       # contract name, e.g. "diffdock_blind_docking"
    title: str                      # human name, e.g. "DiffDock"
    domain: str                     # e.g. "Molecular docking"
    summary: str                    # one line: what it does
    repo_url: str                   # the resurrected source repo
    paper: str
    era: str                        # e.g. "2023 · PyTorch diffusion · GPU"
    license: str
    base_image: str
    gpu: bool = False
    image_public: bool = False      # is the pinned image publicly pullable yet?
    from_url: bool = False          # revived from a bare URL via the Scout?
    turns: Optional[int] = None     # autonomous agent-turns the revival took
    sanity_metric: str = ""
    sanity_threshold: Optional[float] = None
    sanity_direction: str = "above"  # "above": >= threshold passes; "below": < passes
    reproduced_metric: Optional[str] = None
    reproduced_reported: Optional[float] = None
    reproduced_measured: Optional[float] = None
    giveback_pr: Optional[str] = None
    contract: str = ""              # repo-relative path to the contract bundle
    added: str = ""                 # ISO date

    # -- derived -------------------------------------------------------
    @property
    def reproduced(self) -> bool:
        return self.reproduced_measured is not None

    def sanity_str(self) -> str:
        if not self.sanity_metric:
            return "—"
        op = "<" if self.sanity_direction == "below" else "≥"
        return f"{self.sanity_metric} {op} {self.sanity_threshold}"

    def headline(self) -> str:
        """The result a human cares about, in one phrase."""
        if self.reproduced:
            return (f"reproduced the paper — {self.reproduced_metric} "
                    f"{self.reproduced_measured} vs {self.reproduced_reported}")
        return f"revived · smoke {self.sanity_str()}"

    # -- serialization -------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RegistryEntry":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)


# --------------------------------------------------------------------------
# Loading a catalog (local dir or remote index.json / URL)
# --------------------------------------------------------------------------
def _read_url(url: str, timeout: float = 20.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as fh:  # noqa: S310 (trusted host)
        return fh.read()


def load_catalog(source: Optional[str] = None) -> list["RegistryEntry"]:
    """Load registry entries from *source*.

    ``source`` may be: a local ``registry/`` directory, a local or remote
    ``index.json``, or ``None`` (auto: local ``./registry`` if present, else the
    canonical published index). Returns entries sorted by title.
    """
    src = _resolve_source(source)
    if src.startswith("http://") or src.startswith("https://"):
        data = json.loads(_read_url(src))
        entries = [RegistryEntry.from_dict(e) for e in data["entries"]]
    else:
        p = Path(src)
        if p.is_dir():
            edir = p / "entries" if (p / "entries").is_dir() else p
            entries = [RegistryEntry.from_dict(yaml.safe_load(f.read_text()))
                       for f in sorted(edir.glob("*.yaml"))]
        else:  # a json file
            data = json.loads(p.read_text())
            entries = [RegistryEntry.from_dict(e) for e in data["entries"]]
    return sorted(entries, key=lambda e: e.title.lower())


def _resolve_source(source: Optional[str]) -> str:
    if source:
        return source
    if Path("registry").is_dir():
        return "registry"
    return DEFAULT_INDEX_URL


def get(catalog: list["RegistryEntry"], name: str) -> "RegistryEntry":
    for e in catalog:
        if e.name == name or e.title.lower() == name.lower():
            return e
    raise KeyError(f"{name!r} not in registry (have: {', '.join(e.name for e in catalog)})")


# --------------------------------------------------------------------------
# Generated artifacts: index.json + the docs page
# --------------------------------------------------------------------------
def build_index(entries: list["RegistryEntry"]) -> dict:
    return {
        "schema": 1,
        "count": len(entries),
        "entries": [e.to_dict() for e in entries],
    }


def render_markdown(entries: list["RegistryEntry"]) -> str:
    lines = [
        "# Registry",
        "",
        "A living archive of tools Lazarus has brought back from the dead — each revived",
        "from its source repo into a callable, containerised brick with a verified sanity",
        "check, and (where a benchmark exists) a reproduced paper number.",
        "",
        f"**{len(entries)} revived tools.** Pull any of them: `lazarus pull <name>`.",
        "",
        "| Tool | Domain | Era / stack | Result | From a URL |",
        "|---|---|---|---|:--:|",
    ]
    for e in entries:
        result = (f"**{e.reproduced_measured} vs {e.reproduced_reported}** ({e.reproduced_metric})"
                  if e.reproduced else f"smoke {e.sanity_str()}")
        lines.append(f"| **{e.title}** | {e.domain} | {e.era} | {result} | "
                     f"{'✅' if e.from_url else '—'} |")
    lines += ["", "---", ""]
    for e in entries:
        lines += [
            f"## {e.title}  <small>`{e.name}`</small>",
            "",
            f"{e.summary}",
            "",
            f"- **Source:** [{e.repo_url.replace('https://github.com/', '')}]({e.repo_url}) · {e.license}",
            f"- **Stack:** {e.era}" + ("  ·  GPU" if e.gpu else ""),
            f"- **Sanity check:** `{e.sanity_str()}`"
            + (f"  ·  **reproduced the paper:** {e.reproduced_metric} "
               f"**{e.reproduced_measured}** vs {e.reproduced_reported}" if e.reproduced else ""),
            f"- **Revived:** {e.turns} autonomous agent-turns"
            + ("  ·  from a bare URL (Scout-planned)" if e.from_url else ""),
        ]
        if e.giveback_pr:
            lines.append(f"- **Given back:** [{e.giveback_pr.split('/')[-3] + ' PR #' + e.giveback_pr.split('/')[-1]}]({e.giveback_pr})")
        if e.paper:
            lines.append(f"- **Paper:** {e.paper}")
        lines += [
            "",
            f"```bash",
            f"lazarus pull {e.name}",
            f"```",
            "",
            (f"> ℹ️ The pinned image `{e.base_image}` isn't published yet — `pull` fetches the "
             f"contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt."
             if not e.image_public else ""),
            "",
        ]
    return "\n".join(lines).replace("\n\n\n", "\n\n")


# --------------------------------------------------------------------------
# lazarus pull — fetch a contract bundle by name
# --------------------------------------------------------------------------
def pull(name: str, dest: str = ".", source: Optional[str] = None) -> Path:
    """Fetch the contract bundle for *name* into ``dest/<name>/``.

    Works from a local registry (copies the files) or the published one
    (fetches each file over HTTPS). Returns the destination directory.
    """
    catalog = load_catalog(source)
    entry = get(catalog, name)
    out = Path(dest) / entry.name
    out.mkdir(parents=True, exist_ok=True)

    src = _resolve_source(source)
    local_root = None
    if not src.startswith("http"):
        root = Path(src)
        local_root = root.parent if root.name in ("registry", "index.json") else root
        if not (local_root / entry.contract).is_dir():
            local_root = None  # fall back to remote fetch

    grabbed = []
    for fname in CONTRACT_FILES:
        try:
            if local_root is not None:
                srcf = local_root / entry.contract / fname
                if not srcf.exists():
                    continue
                (out / fname).write_bytes(srcf.read_bytes())
            else:
                data = _read_url(f"{RAW_BASE}/{entry.contract}/{fname}")
                (out / fname).write_bytes(data)
            grabbed.append(fname)
        except Exception:  # noqa: BLE001 — a missing optional file shouldn't fail the pull
            continue
    if not grabbed:
        raise RuntimeError(f"could not fetch any contract files for {entry.name}")
    return out
