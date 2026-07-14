#!/usr/bin/env python3
"""The Lazarus benchmark harness.

Point it at comp-bio repo URLs; for each it runs `lazarus resurrect` from the
bare URL (Scout-planned) under hard turn/time caps, classifies the outcome into
a reason code, and appends a row to ``benchmark/results.json``. Successes can be
auto-landed into the registry.

    python benchmark/run.py --repos benchmark/pilot_repos.txt \
        --docker-host ssh://you@gpu-box --max-turns 90 --timeout 5400 --land

The pure pieces (the schema, `classify`, results IO, `provisional_entry`) are
unit-tested; `run_one` drives the real agent and needs Docker + Claude auth.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# The benchmark applies its OWN reproduction criterion — never the agent's
# self-declared tolerance (an agent can set that loose to self-award a pass).
# "reproduced" = the measured number is within this relative band of the paper's.
REPRODUCE_REL_TOL = 0.15


def reproduced_ok(measured, reported, rel_tol: float = REPRODUCE_REL_TOL) -> bool:
    if measured is None or reported in (None, 0):
        return False
    return abs(measured - reported) <= rel_tol * abs(reported)


# reason codes — success first, then the failure taxonomy (see benchmark/README.md)
SUCCESS = ("reproduced", "revived", "runs-unverified")
FAILURE = ("weights-gone", "data-gated", "hardware-incompatible",
           "unresolvable-deps", "license-blocked", "budget-exceeded")
# not a *method* outcome — the harness/host couldn't even start (bad base image,
# pull timeout). Kept out of the revival-rate denominator; retry these.
INFRA = ("infra-failed",)
REASONS = SUCCESS + FAILURE


@dataclass
class BenchmarkResult:
    repo_url: str
    outcome: str = ""                       # a reason code
    name: str = ""                          # emitted contract name (if success)
    turns: int = 0
    wall_clock_s: float = 0.0
    cost_usd: Optional[float] = None
    naive_runs: Optional[bool] = None       # baseline: ran without the agent? (filled separately)
    sanity_metric: str = ""
    sanity_threshold: Optional[float] = None
    reproduced_reported: Optional[float] = None
    reproduced_measured: Optional[float] = None
    verified: Optional[bool] = None         # did WE re-run the smoke and see it pass?
    base_image: str = ""
    summary: str = ""                       # the Scout's capability line
    attempted_at: str = ""                  # ISO date (stamped by the caller)
    notes: str = ""

    @property
    def revived(self) -> bool:
        return self.outcome in SUCCESS

    @property
    def reproduced(self) -> bool:
        return self.outcome == "reproduced"

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Outcome classification (pure — unit-tested)
# --------------------------------------------------------------------------
_FAILURE_SIGNALS = [
    ("weights-gone", ("weights", "checkpoint", "pretrained", "model file")),
    ("data-gated", ("dataset", "gated", "credential", "registration", "license agreement", "access request")),
    ("hardware-incompatible", ("sigill", "illegal instruction", "compute capability",
                               "no cuda", "requires gpu", "no gpu", "avx")),
    ("license-blocked", ("no-derivative", "noderiv", "non-commercial", "cc by-nc-nd")),
]


def classify(*, completed: bool, is_error: bool, contract_emitted: bool,
             reproduced: bool, revived: bool, timed_out: bool,
             hit_turn_cap: bool, final_text: str = "") -> str:
    """Map a run's end-state to a reason code.

    Success is authoritative (a contract was emitted and its checks held);
    failures are inferred from the final text with a coarse keyword pass, falling
    back to ``unresolvable-deps``. The agent's own final report is the strongest
    signal, so keep failure text specific.
    """
    if contract_emitted and completed and not is_error:
        if reproduced:
            return "reproduced"
        if revived:
            return "revived"
        return "runs-unverified"

    if timed_out or hit_turn_cap:
        return "budget-exceeded"

    text = (final_text or "").lower()
    # a "gone/404/unavailable" note near a weights mention is the classic dead-weights case
    if any(k in text for k in ("weights", "checkpoint", "pretrained")) and \
       any(k in text for k in ("404", "not found", "no longer", "unavailable", "gone", "dead link", "removed")):
        return "weights-gone"
    for reason, keys in _FAILURE_SIGNALS:
        if any(k in text for k in keys):
            return reason
    return "unresolvable-deps"


# --------------------------------------------------------------------------
# Independent verification — re-run the emitted smoke in its own image and
# confirm WE see it pass. No agent, no rebuild: it reuses the snapshot the
# resurrection already produced, so it's one short container run, not a redo.
# --------------------------------------------------------------------------
_LOWER_IS_BETTER = ("rmsd", "loss", "mae", "mse", "error", "distance", "perplexity")


def interpret_smoke(output: str, metric: Optional[str] = None,
                    threshold: Optional[float] = None) -> Optional[bool]:
    """Decide pass/fail from a smoke run's output. Prefers an explicit PASS/FAIL
    token; else extracts the metric and compares to threshold (direction inferred
    from the metric name). Returns None when it genuinely can't tell."""
    # Authoritative verdict = a standalone UPPERCASE PASS/FAIL, which the emitted
    # smokes print deliberately. Case-sensitive so prose noise like
    # "mesg: ttyname failed: Inappropriate ioctl for device" (a non-TTY docker
    # warning) does NOT read as a failure.
    has_pass = re.search(r"\bPASS\b", output) is not None
    has_fail = re.search(r"\bFAIL\b", output) is not None
    if has_pass and not has_fail:
        return True
    if has_fail and not has_pass:
        return False
    # no explicit verdict → compare the metric to its threshold
    if metric and threshold is not None:
        m = re.search(rf"{re.escape(metric)}\s*[=:]\s*(-?\d+(?:\.\d+)?)", output, re.I)
        if not m:  # fall back to the last number printed
            nums = re.findall(r"-?\d+(?:\.\d+)?", output)
            m = nums[-1] if nums else None
            val = float(m) if m else None
        else:
            val = float(m.group(1))
        if val is not None:
            below = any(k in metric.lower() for k in _LOWER_IS_BETTER)
            return (val <= threshold) if below else (val >= threshold)
    return None


def pull_image(image: str, docker_host: Optional[str] = None, timeout_s: int = 1800) -> bool:
    """Pull ``image`` on the docker host. Returns True if it now exists locally.
    Doubles as an existence check (a non-existent tag fails fast) and pre-warms the
    sandbox so its start doesn't time out on a big image."""
    from lazarus.sandbox import DockerClient, find_docker
    client = DockerClient(binary=find_docker(), docker_host=docker_host)
    try:
        cr = client.run(["pull", "--platform", "linux/amd64", image], timeout=timeout_s)
        return cr.exit_code == 0
    except Exception:  # noqa: BLE001
        return False


def verify_smoke(contract, docker_host: Optional[str] = None,
                 timeout_s: int = 900) -> tuple[Optional[bool], str]:
    """Run ``contract.smoke.command`` in ``contract.base_image`` and interpret it.
    Returns (passed | None, combined output)."""
    from lazarus.sandbox import DockerClient, find_docker

    if not contract.smoke or not contract.smoke.command:
        return None, "no smoke command in contract"
    client = DockerClient(binary=find_docker(), docker_host=docker_host)
    args = ["run", "--rm", "--platform", contract.platform or "linux/amd64"]
    if getattr(contract, "gpus", ""):
        args += ["--gpus", contract.gpus]
    args += [contract.base_image, "bash", "-lc", contract.smoke.command]
    try:
        cr = client.run(args, timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001
        return None, f"verify run error: {exc}"
    out = (cr.stdout or "") + "\n" + (cr.stderr or "")
    passed = interpret_smoke(out, contract.smoke.metric, contract.smoke.threshold)
    return passed, out[-2000:]


# --------------------------------------------------------------------------
# Results IO (append-only, resumable at the corpus level)
# --------------------------------------------------------------------------
def load_results(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def save_results(path: str, rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(rows, indent=2, ensure_ascii=False))


def already_done(rows: list[dict], repo_url: str) -> bool:
    # infra-failed is not terminal — leave it retryable on the next sweep
    return any(r.get("repo_url") == repo_url and r.get("outcome")
               and r.get("outcome") not in INFRA for r in rows)


# --------------------------------------------------------------------------
# Provisional registry entry from a successful run (best-effort; needs curation)
# --------------------------------------------------------------------------
def provisional_entry(contract, plan, result: BenchmarkResult, added: str):
    """Build a RegistryEntry from an emitted contract + Scout plan.

    Fills what's mechanical; leaves the human-curated fields (domain, era,
    license, title polish) blank so they're an obvious 'needs curation' signal.
    """
    from lazarus.registry import RegistryEntry

    bench = getattr(contract, "benchmark", None)
    smoke = getattr(contract, "smoke", None)
    return RegistryEntry(
        name=contract.name,
        title=contract.name.replace("_", " ").title(),
        domain="",                                  # curate
        summary=getattr(plan, "capability", "") or result.summary,
        repo_url=contract.repo_url or result.repo_url,
        paper=getattr(contract, "paper", "") or "",
        era="",                                     # curate
        license="",                                 # curate
        base_image=contract.base_image,
        gpu=bool(getattr(contract, "gpus", "")),
        from_url=True,
        turns=result.turns,
        sanity_metric=getattr(smoke, "metric", "") if smoke else "",
        sanity_threshold=getattr(smoke, "threshold", None) if smoke else None,
        reproduced_metric=getattr(bench, "metric", None) if bench else None,
        reproduced_reported=getattr(bench, "reported", None) if bench else None,
        reproduced_measured=getattr(bench, "measured", None) if bench else None,
        contract=result.notes or "",               # caller sets the contract path
        added=added,
    )


# --------------------------------------------------------------------------
# The real run (drives the agent; not exercised by unit tests)
# --------------------------------------------------------------------------
def run_one(repo_url: str, *, docker_host: Optional[str], max_turns: int = 90,
            timeout_s: int = 5400, out_root: str = "benchmark/output",
            model: Optional[str] = None, verify: bool = True,
            on_event=None) -> BenchmarkResult:
    import asyncio
    import time

    from lazarus.scout import scout
    from lazarus.resurrect import Resurrector
    from lazarus.contract import Contract

    slug = repo_url.rstrip("/").split("/")[-1].lower()
    out_dir = str(Path(out_root) / slug)
    t0 = time.time()
    res = BenchmarkResult(repo_url=repo_url)

    # 1) plan from the URL (host-side, cheap)
    try:
        plan = asyncio.run(scout(repo_url, model=model))
    except Exception as exc:  # noqa: BLE001
        res.outcome, res.notes = "infra-failed", f"scout failed: {exc}"
        res.wall_clock_s = time.time() - t0
        return res
    res.summary, res.base_image = plan.capability, plan.base_image

    # 1.5) ensure the base image is real and pre-pulled. If the Scout picked a
    #      non-existent tag (the pilot's TAPE case), re-plan once with a correction;
    #      pre-pulling also stops the sandbox from timing out on a big image (DeepDTA).
    if not pull_image(plan.base_image, docker_host):
        try:
            plan2 = asyncio.run(scout(repo_url, model=model, hint=(
                f"The base image '{plan.base_image}' is NOT pullable — it does not exist "
                f"on the registry. Choose a DIFFERENT, currently-available base image.")))
        except Exception:  # noqa: BLE001
            plan2 = None
        if plan2 is not None and pull_image(plan2.base_image, docker_host):
            plan = plan2
            res.summary, res.base_image = plan.capability, plan.base_image
        else:
            res.outcome = "infra-failed"
            res.notes = f"base image not pullable: {plan.base_image}"
            res.wall_clock_s = time.time() - t0
            return res

    # 2) resurrect under caps (count tool calls so a timeout still reports turns)
    turn_est = [0]

    def _ev(e):
        if e.kind == "tool_use":
            turn_est[0] += 1
        if on_event:
            on_event(e)

    r = Resurrector(image=plan.base_image, docker_host=docker_host, max_turns=max_turns,
                    keep_container=True, output_dir=out_dir,
                    gpus="all" if plan.needs_gpu else None, model=model, on_event=_ev)
    timed_out = False
    result = None
    try:
        result = asyncio.run(asyncio.wait_for(r.resurrect(plan.to_goal()), timeout=timeout_s))
    except asyncio.TimeoutError:
        timed_out = True
    except Exception as exc:  # noqa: BLE001
        res.notes = f"run error: {exc}"
    finally:
        if r.sandbox is not None:
            try:
                r.sandbox.stop()
            except Exception:  # noqa: BLE001
                pass

    res.wall_clock_s = time.time() - t0
    if result is not None:
        res.turns, res.cost_usd = result.num_turns, result.cost_usd
    elif timed_out:
        res.turns = turn_est[0]          # timeout: no final message → estimate from tool calls
    else:
        # the resurrect raised before producing a result (sandbox start, etc.) — infra, not science
        res.turns = turn_est[0]
        res.outcome = "infra-failed"
        res.notes = res.notes or "resurrection failed to start"
        return res

    # 3) inspect the emitted contract (if any) and classify
    contract, reproduced, revived = None, False, False
    cpath = Path(out_dir) / "lazarus.yaml"
    if cpath.exists():
        try:
            contract = Contract.from_yaml(cpath.read_text())
            res.name = contract.name
            res.base_image = contract.base_image  # the final snapshot, not the Scout's start image
            if contract.smoke:
                res.sanity_metric, res.sanity_threshold = contract.smoke.metric, contract.smoke.threshold
                revived = True
            if contract.benchmark and contract.benchmark.measured is not None:
                res.reproduced_reported = contract.benchmark.reported
                res.reproduced_measured = contract.benchmark.measured
                # harness criterion, NOT the agent's self-declared tolerance
                reproduced = reproduced_ok(contract.benchmark.measured, contract.benchmark.reported)
        except Exception as exc:  # noqa: BLE001
            res.notes += f" | contract parse: {exc}"

    res.outcome = classify(
        completed=bool(result and result.completed),
        is_error=bool(result and result.is_error),
        contract_emitted=contract is not None,
        reproduced=reproduced, revived=revived,
        timed_out=timed_out, hit_turn_cap=bool(result and result.num_turns >= max_turns),
        final_text=(result.final_text if result else ""),
    )

    # 4) independently verify a claimed success by re-running its smoke in-image
    if verify and contract is not None and res.outcome in SUCCESS:
        passed, vout = verify_smoke(contract, docker_host=docker_host)
        res.verified = passed
        if passed is False:  # agent's contract doesn't actually pass on our re-run
            res.outcome = "runs-unverified"
            res.notes = (res.notes + " | independent smoke re-run FAILED").strip(" |")
        elif passed is None:
            res.notes = (res.notes + " | verification inconclusive").strip(" |")
    return res


def main(argv=None) -> int:
    import argparse
    import time

    ap = argparse.ArgumentParser(description="Lazarus benchmark harness")
    ap.add_argument("--repos", help="file with one repo URL per line (# comments ok)")
    ap.add_argument("--url", action="append", help="a single repo URL (repeatable)")
    ap.add_argument("--docker-host", default=None)
    ap.add_argument("--max-turns", type=int, default=90)
    ap.add_argument("--timeout", type=int, default=5400, help="per-repo wall-clock cap (s)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default="benchmark/results.json")
    ap.add_argument("--land", action="store_true", help="auto-land successes into the registry")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the independent smoke re-run (trust the agent's claim)")
    args = ap.parse_args(argv)

    from lazarus.cli import load_dotenv
    load_dotenv()

    urls = list(args.url or [])
    if args.repos:
        for line in Path(args.repos).read_text().splitlines():
            line = line.split("#")[0].strip()
            if line:
                urls.append(line)
    if not urls:
        print("no repos given (--repos FILE or --url URL)")
        return 2

    rows = load_results(args.out)
    today = time.strftime("%Y-%m-%d")
    for url in urls:
        if already_done(rows, url):
            print(f"skip (done): {url}")
            continue
        print(f"\n=== {url} ===", flush=True)
        res = run_one(url, docker_host=args.docker_host, max_turns=args.max_turns,
                      timeout_s=args.timeout, model=args.model, verify=not args.no_verify,
                      on_event=lambda e: print(f"  {e.kind}: {e.text[:200]}", flush=True))
        res.attempted_at = today
        rows = [r for r in rows if r.get("repo_url") != url] + [res.to_dict()]
        save_results(args.out, rows)
        print(f"  -> {res.outcome}  ({res.turns} turns, {res.wall_clock_s:.0f}s, "
              f"${res.cost_usd if res.cost_usd is not None else '?'})")
        if args.land and res.revived:
            print("  (landing in registry — provisional entry; curate before publishing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
