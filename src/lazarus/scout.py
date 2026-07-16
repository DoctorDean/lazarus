"""The Scout — turn a bare repo URL into a resurrection plan.

Today an operator hands the sandbox agent a curated ``--image`` and a
hand-written ``--goal-file`` (the task *and* the sanity check that defines
"revived"). The Scout removes that expert step: given only a GitHub URL, it
reads the repo the way a newcomer would — the README, the requirements, the
entry scripts, the linked paper — and drafts the plan itself.

Integrity note: the Scout is the *one* Lazarus step allowed to see the outside
world (WebFetch/WebSearch), because that is exactly the public information any
stranger has. It never loads the operator's notes, memory, or project settings
(``setting_sources=[]``), so the downstream resurrection stays honest — it is
solved from the public repo, not from a walkthrough.

The plan the Scout emits (:class:`ResurrectionPlan`) feeds straight into the
existing :class:`~lazarus.resurrect.Resurrector`: a base image to start from,
whether a GPU is needed, and a goal string whose first instruction is to
``git clone`` the repo into the sandbox.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Optional

# NOTE: claude_agent_sdk is imported lazily inside scout() so that the pure
# planning logic (plan_from_text / ResurrectionPlan) — and its tests — work
# without the optional `agent` extra installed.

SCOUT_SYSTEM_PROMPT = """\
You are Lazarus Scout. Given a public GitHub repository for a computational-science
method, you plan its resurrection: you decide what the method's headline capability
is, how to PROVE a revival works, and what environment to attempt it in.

You see only what any newcomer sees — the public repo and its paper. Investigate:
- the README and any docs (what does the method DO — the one famous input -> output?);
- setup.py / requirements.txt / environment.yml / Dockerfile (the dependency era);
- the entry scripts and the paper (find where a fresh input becomes the headline
  output — inference, not training);
- whether pretrained weights ship or are downloadable, and what a SMALL test input is.

Then output ONE fenced ```json block (and nothing after it) with EXACTLY these keys:
{
  "capability": "<one sentence: the concrete fresh-input -> headline-output this revival targets>",
  "base_image": "<ONLY a bare Docker image reference and nothing else — no prose, no parenthetical, no 'if unavailable' fallback. STRONGLY prefer an image the repo/README itself endorses if one exists (that image usually has the stack prebuilt); else a sensible base like 'python:3.9', 'continuumio/miniconda3', or 'nvidia/cuda:11.1.1-cudnn8-devel-ubuntu20.04'. Example valid values: 'lzamparo/basset', 'python:3.6'>",
  "needs_gpu": <true|false>,
  "test_input": "<the smallest concrete input to run the sanity check on, and where it comes from (a file the repo ships, or a specific public URL/accession)>",
  "sanity_metric": "<short name of the number that proves it worked, e.g. 'roc_auc', 'pearson_r', 'top1_matches_reference'; or 'qualitative' if no metric applies>",
  "sanity_threshold": <a number the metric must reach to count as revived, or null if qualitative>,
  "sanity_description": "<how to compute/verify the sanity check on the test input; must be concretely checkable, not vague>",
  "goal_text": "<the task to hand the sandbox agent: what capability to make runnable and how to prove it, phrased as an instruction. Do NOT include the git clone line; that is added automatically>",
  "paper": "<citation or URL of the method's paper, or '' if none found>",
  "notes": "<the single biggest resurrection risk you anticipate, in one sentence>"
}

Rules:
- The sanity check MUST be falsifiable: a metric+threshold on a named input, or a
  qualitative assertion that could clearly fail (e.g. 'outputs 3+ pockets on 1FKF').
  A revival that cannot fail proves nothing.
- Prefer inference on ONE small input. Never plan around a bulk/training dataset.
- If pretrained weights are needed and you found where they live, say so in test_input/goal_text.
- Be specific and honest. If the repo looks unrevivable in a bounded run, still produce
  the best plan and flag the risk in notes.
"""


@dataclass
class ResurrectionPlan:
    repo_url: str
    capability: str
    base_image: str
    needs_gpu: bool
    test_input: str
    sanity_metric: str
    sanity_threshold: Optional[float]
    sanity_description: str
    goal_text: str
    paper: str = ""
    notes: str = ""
    raw: str = field(default="", repr=False)  # the model's full final text

    def to_goal(self) -> str:
        """Assemble the instruction handed to the sandbox Resurrector.

        The sandbox agent is web-blocked, so it must fetch the repo itself: the
        goal's first move is a shallow clone into the working directory.
        """
        thr = (
            f" (target {self.sanity_metric} >= {self.sanity_threshold})"
            if self.sanity_threshold is not None
            else ""
        )
        return (
            f"Resurrect this repository: {self.repo_url}\n\n"
            f"FIRST, get the code into the container. It MAY already be baked into this "
            f"base image (check, e.g. search the filesystem for a signature file from the "
            f"repo). If it is NOT already present, clone it:\n"
            f"    git clone --depth 1 {self.repo_url} repo && cd repo\n"
            f"(install git with the system package manager if it is missing. If the repo is "
            f"already in the image, use that copy and its configured paths.)\n\n"
            f"CAPABILITY TO REVIVE:\n{self.capability}\n\n"
            f"TASK:\n{self.goal_text}\n\n"
            f"SANITY CHECK (this is how a revival is judged{thr}):\n"
            f"{self.sanity_description}\n\n"
            f"TEST INPUT:\n{self.test_input}\n"
        )

    def summary(self) -> str:
        gpu = "yes" if self.needs_gpu else "no"
        thr = self.sanity_threshold if self.sanity_threshold is not None else "—"
        return (
            f"Resurrection plan for {self.repo_url}\n"
            f"  capability : {self.capability}\n"
            f"  base image : {self.base_image}   (gpu: {gpu})\n"
            f"  test input : {self.test_input}\n"
            f"  sanity     : {self.sanity_metric} >= {thr} — {self.sanity_description}\n"
            f"  paper      : {self.paper or '—'}\n"
            f"  top risk   : {self.notes or '—'}"
        )


_REQUIRED = (
    "capability", "base_image", "needs_gpu", "test_input",
    "sanity_metric", "sanity_description", "goal_text",
)


def _extract_json(text: str) -> dict:
    """Pull the last ```json fenced block (or last bare {...}) out of the text."""
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = blocks[-1] if blocks else None
    if candidate is None:
        start = text.rfind("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
    if candidate is None:
        raise ValueError("Scout produced no JSON plan block")
    return json.loads(candidate)


_IMAGE_RE = re.compile(r"^[A-Za-z0-9][\w.\-/]*(?::[\w.\-]+)?(?:@sha256:[a-f0-9]+)?$")


def _sanitize_image(value: str) -> str:
    """Coerce the Scout's base_image field to a bare, valid Docker reference.

    The model sometimes appends prose ('python:3.9 (a slim base)') or a fallback
    ('kaixhin/cuda-torch:latest. If unavailable, build ...'). A whole sentence
    reaching ``docker run`` is a hard 'invalid reference format' crash, so keep
    only the leading token and require it to look like an image reference.
    """
    token = value.strip().split()[0].rstrip(".,;") if value.strip() else ""
    if not _IMAGE_RE.match(token):
        raise ValueError(
            f"Scout base_image is not a valid Docker reference: {value!r} "
            f"(parsed {token!r}). Re-run the Scout or pass --image explicitly."
        )
    return token


def _coerce_threshold(value) -> Optional[float]:
    if value is None or value == "" or value == "null":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def plan_from_text(repo_url: str, text: str) -> ResurrectionPlan:
    """Parse + validate a Scout plan from the agent's final message text."""
    data = _extract_json(text)

    def _absent(value) -> bool:
        # a present ``False`` (e.g. needs_gpu) is NOT missing; empty strings are
        return value is None or (isinstance(value, str) and not value.strip())

    missing = [k for k in _REQUIRED if _absent(data.get(k))]
    if missing:
        raise ValueError(f"Scout plan missing required field(s): {missing}")

    metric = str(data["sanity_metric"]).strip()
    threshold = _coerce_threshold(data.get("sanity_threshold"))
    qualitative = metric.lower() in {"qualitative", "none", ""}
    if not qualitative and threshold is None:
        raise ValueError(
            f"Scout plan sanity check is not falsifiable: metric {metric!r} has no "
            f"numeric threshold and is not declared 'qualitative'"
        )

    return ResurrectionPlan(
        repo_url=repo_url,
        capability=str(data["capability"]).strip(),
        base_image=_sanitize_image(str(data["base_image"])),
        needs_gpu=bool(data["needs_gpu"]),
        test_input=str(data["test_input"]).strip(),
        sanity_metric=metric,
        sanity_threshold=threshold,
        sanity_description=str(data["sanity_description"]).strip(),
        goal_text=str(data["goal_text"]).strip(),
        paper=str(data.get("paper", "")).strip(),
        notes=str(data.get("notes", "")).strip(),
        raw=text,
    )


def find_claude_cli() -> Optional[str]:
    exe = shutil.which("claude")
    if exe:
        return exe
    cand = os.path.expanduser("~/.local/bin/claude")
    return cand if os.path.exists(cand) else None


async def scout(
    repo_url: str,
    *,
    model: Optional[str] = None,
    cli_path: Optional[str] = None,
    max_turns: int = 30,
    hint: str = "",
    on_text=None,
) -> ResurrectionPlan:
    """Investigate ``repo_url`` on the web and return a validated plan.

    Runs a host-side agent with only web tools — no sandbox, no operator notes.
    """
    from claude_agent_sdk import (  # lazy: only the live path needs the SDK
        AssistantMessage,
        ClaudeAgentOptions,
        TextBlock,
        query,
    )

    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch", "WebSearch"],
        setting_sources=[],  # never read host CLAUDE.md / memory / project settings
        system_prompt=SCOUT_SYSTEM_PROMPT,
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        model=model,
        cli_path=cli_path or find_claude_cli(),
    )
    prompt = (
        f"Investigate this repository and produce its resurrection plan as the "
        f"specified JSON block: {repo_url}"
    )
    if hint:
        prompt += f"\n\nIMPORTANT CORRECTION: {hint}"
    final_text = ""
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    final_text = block.text
                    if on_text:
                        on_text(block.text)
    if not final_text.strip():
        raise ValueError("Scout returned no text; cannot form a plan")
    return plan_from_text(repo_url, final_text)
