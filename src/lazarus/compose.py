"""Lazarus Compose — stitch resurrected components into a pipeline.

Every resurrection emits the same :class:`~lazarus.contract.Contract` (typed
inputs/outputs + a containerised entrypoint), so a revived tool is a composable
*brick* regardless of its domain, language, or era. A pipeline is a small YAML
that wires bricks together; the runner executes each brick's container on the
configured host (local / remote / GPU, same flags as the sandbox), passes file
artifacts between steps, and collects the outputs.

Component execution model (uniform across all bricks):
- each ``with:`` value is either a **literal** (-> an env var of that name) or a
  **file reference** ``${...}`` (-> the file is copied to /lazarus/in/<name>/ and
  an env var of that name points at it in the container);
- ``$OUTDIR`` is always ``/lazarus/out``; whatever the entrypoint writes there is
  collected and becomes available to later steps as ``${stepid.<selector>}``.

This is exactly the interface the emitted contracts already speak, so the three
resurrected methods compose with no changes.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yaml

from lazarus.contract import Contract
from lazarus.sandbox import DockerClient, Sandbox, find_docker


# --------------------------------------------------------------------------
# Registry — the brick library
# --------------------------------------------------------------------------
@dataclass
class Registry:
    components: dict  # name -> Contract

    @classmethod
    def from_dirs(cls, dirs) -> "Registry":
        comps: dict = {}
        for d in dirs:
            for yml in sorted(Path(d).rglob("lazarus.yaml")):
                c = Contract.from_yaml(yml.read_text(encoding="utf-8"))
                comps[c.name] = c
        return cls(comps)

    def get(self, name: str) -> Contract:
        if name not in self.components:
            raise KeyError(
                f"component {name!r} not in registry (have: {sorted(self.components)})"
            )
        return self.components[name]


# --------------------------------------------------------------------------
# Pipeline spec
# --------------------------------------------------------------------------
@dataclass
class Step:
    id: str
    uses: str
    with_: dict = field(default_factory=dict)


@dataclass
class Pipeline:
    name: str
    inputs: dict = field(default_factory=dict)     # name -> {type: ...}
    steps: list = field(default_factory=list)      # list[Step]
    outputs: dict = field(default_factory=dict)    # name -> ref string

    @classmethod
    def from_yaml(cls, text: str) -> "Pipeline":
        d = yaml.safe_load(text) or {}
        steps = [
            Step(id=s["id"], uses=s["uses"], with_=s.get("with", {}) or {})
            for s in (d.get("steps") or [])
        ]
        return cls(
            name=d.get("name", "pipeline"),
            inputs=d.get("inputs") or {},
            steps=steps,
            outputs=d.get("outputs") or {},
        )


def _is_ref(v) -> bool:
    return isinstance(v, str) and v.strip().startswith("${") and v.strip().endswith("}")


def _ref_body(v: str) -> str:
    return v.strip()[2:-1].strip()


def _deps_of(step: Step) -> set:
    """Ids of other steps this step depends on (via ${stepid.*} refs)."""
    deps = set()
    for v in step.with_.values():
        if _is_ref(v):
            head = _ref_body(v).split(".")[0]
            if head != "inputs":
                deps.add(head)
    return deps


def toposort(steps: list) -> list:
    """Order steps so every dependency runs before its dependents."""
    by_id = {s.id: s for s in steps}
    order: list = []
    seen, temp = set(), set()

    def visit(sid: str) -> None:
        if sid in seen:
            return
        if sid in temp:
            raise ValueError(f"pipeline has a cycle at step {sid!r}")
        temp.add(sid)
        for dep in _deps_of(by_id[sid]):
            if dep in by_id:
                visit(dep)
        temp.discard(sid)
        seen.add(sid)
        order.append(sid)

    for s in steps:
        visit(s.id)
    return [by_id[i] for i in order]


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
@dataclass
class StepResult:
    id: str
    out_dir: str
    files: list = field(default_factory=list)


class Runner:
    def __init__(
        self,
        registry: Registry,
        *,
        docker_host: Optional[str] = None,
        container_workdir: str = "/lazarus",
        on_event: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.registry = registry
        self.client = DockerClient(binary=find_docker(), docker_host=docker_host)
        self.container_workdir = container_workdir
        self.on_event = on_event

    def _emit(self, msg: str) -> None:
        if self.on_event:
            self.on_event(msg)

    def _resolve(self, value, ctx: dict):
        """Return ('literal', str) or ('file', host_path)."""
        if not _is_ref(value):
            return ("literal", str(value))
        head, *rest = _ref_body(value).split(".")
        if head == "inputs":
            return ("file", ctx["inputs"][rest[0]])
        step_out = ctx["steps"][head].out_dir
        if not rest:
            return ("file", step_out)
        selector = rest[0]
        matches = sorted(glob.glob(os.path.join(step_out, f"*{selector}*")))
        if not matches:
            raise FileNotFoundError(
                f"no output matching {selector!r} in step {head!r} ({step_out})"
            )
        return ("file", matches[0])

    def run(self, pipeline: Pipeline, inputs: dict, out_root) -> "tuple[dict, dict]":
        out_root = Path(out_root)
        out_root.mkdir(parents=True, exist_ok=True)
        ctx = {
            "inputs": {k: str(Path(v).resolve()) for k, v in inputs.items()},
            "steps": {},
        }
        results: dict = {}
        for step in toposort(pipeline.steps):
            contract = self.registry.get(step.uses)
            resolved = {k: self._resolve(v, ctx) for k, v in step.with_.items()}
            step_out = out_root / step.id
            self._emit(f"▶ {step.id}  ({step.uses})")
            self._run_component(contract, resolved, step_out)
            files = sorted(str(p) for p in step_out.rglob("*") if p.is_file())
            res = StepResult(step.id, str(step_out), files)
            ctx["steps"][step.id] = res
            results[step.id] = res
            self._emit(f"✓ {step.id}: {len(files)} output file(s)")

        outputs = {name: self._resolve(ref, ctx)[1] for name, ref in pipeline.outputs.items()}
        return outputs, results

    def _run_component(self, contract: Contract, resolved: dict, step_out) -> None:
        step_out = Path(step_out)
        step_out.mkdir(parents=True, exist_ok=True)
        box = Sandbox(
            self.client,
            contract.base_image,
            gpus=(contract.gpus or None),
            workdir=self.container_workdir,
        )
        box.start()
        try:
            box.exec("mkdir -p /lazarus/in /lazarus/out").raise_for_status()
            env = {"OUTDIR": "/lazarus/out"}
            for name, (kind, val) in resolved.items():
                if kind == "file":
                    base = os.path.basename(val.rstrip("/")) or name
                    box.exec(f"mkdir -p /lazarus/in/{name}").raise_for_status()
                    box.put(val, f"/lazarus/in/{name}/{base}")
                    env[name] = f"/lazarus/in/{name}/{base}"
                else:
                    env[name] = val
            box.exec(contract.entrypoint, env=env, timeout=3600).raise_for_status()
            box.get("/lazarus/out/.", str(step_out))
        finally:
            box.stop()
