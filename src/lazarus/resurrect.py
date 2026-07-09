"""The autonomous resurrection loop.

``Resurrector`` starts a sandbox from a base image, hands Claude the container
tools, and drives a bounded build -> run -> read-traceback -> repair loop toward
a goal, streaming events so the run is watchable.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Callable, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

from lazarus.sandbox import DockerClient, Sandbox, find_docker
from lazarus.tools import SERVER_NAME, build_server

SYSTEM_PROMPT = """\
You are Lazarus: you resurrect dead research code and make a buried capability
callable, then PROVE it runs on a fresh input.

You work ONLY through the provided container tools (sandbox_run, sandbox_write_file,
sandbox_read_file, sandbox_snapshot, pin_dependencies). All execution happens
inside the sandbox container; container state persists across sandbox_run calls.
You cannot touch the host. Verify everything by running it — never assume.

Method:
1. ORIENT — Explore the repo and locate the REAL capability the user asked for:
   the concrete code path from a fresh input to the headline output. Read the
   entry scripts and the modules they call.
2. REVIVE — Make that path actually run. On failure, read the ACTUAL traceback and
   fix THAT specific cause with the smallest change that works. Re-run to confirm.
3. CARVE — Reduce it to the minimal command sequence from one input file to the
   output, skipping training/bulk-data-prep not needed for inference.
4. PROVE — Run the user's sanity check on the known input and report the metric.

Hard-won repair heuristics:
- A missing external binary is often present but off PATH — find it (`which`, `find /`)
  and symlink or export PATH rather than reinstalling.
- A rotted download URL: prefer feeding a local input file directly if the tool
  supports it, bypassing the network entirely.
- A prebuilt binary that ABORTS on missing CPU instructions (e.g. "compiled to use
  AVX instructions, but these aren't available") means it's running under emulation
  without those instructions. Install a build compiled without them. For TensorFlow,
  official versions <= 1.5.0 are the last without AVX; the checkpoint and graph-mode
  API are stable across TF 1.x, so a downgrade usually restores pretrained inference.
- When pip pulls too-new, incompatible dependencies, pin them to the repo's commit
  era with pin_dependencies, and constrain transitive pins (numpy/protobuf) as needed.
- Snapshot after each expensive success (a resolved binary chain, a working import)
  so a later failure re-runs from the checkpoint, not from scratch.

Environmental vs. code blockers: try software fixes first (downgrade, non-AVX
build, PATH). But if a CLOSED-SOURCE or prebuilt binary that you cannot replace or
downgrade fails with SIGILL / "illegal instruction" or a CPU-feature abort under
emulation, the sandbox HOST lacks the required native CPU support and no in-sandbox
fix exists. Do not spin: verify it concisely (does a trivial input also fail?),
then STOP and report that this resurrection requires a native host of the right
architecture (e.g. native x86-64), naming the exact offending binary and evidence.

Be surgical and incremental. Once the capability runs on a fresh input and the sanity
check passes, snapshot the working image, then call emit_contract ONCE to write the
integration package (its entrypoint is a bash template using $INPUT and $OUTDIR that
reproduces your minimal command). Finally, state the exact minimal command, where the
output lands, and the sanity metric you measured.
"""

# Built-in tools the resurrection agent must NOT have: it works only through the
# container. Blocking host filesystem/exec/web keeps the run honest (no reading
# the operator's notes) and scoped to the sandbox.
HOST_TOOLS_BLOCKLIST = [
    "Read", "Write", "Edit", "MultiEdit", "NotebookEdit",
    "Bash", "BashOutput", "KillShell",
    "Glob", "Grep", "WebSearch", "WebFetch", "Task", "TodoWrite",
]


def find_claude_cli() -> Optional[str]:
    exe = shutil.which("claude")
    if exe:
        return exe
    cand = os.path.expanduser("~/.local/bin/claude")
    return cand if os.path.exists(cand) else None


@dataclass
class ResurrectionEvent:
    kind: str      # "text" | "tool_use" | "tool_result" | "result"
    text: str


@dataclass
class ResurrectionResult:
    completed: bool
    is_error: bool
    final_text: str
    events: list[ResurrectionEvent] = field(default_factory=list)
    num_turns: int = 0
    snapshots: list[str] = field(default_factory=list)
    output_dir: str = ""


class Resurrector:
    def __init__(
        self,
        image: str,
        *,
        docker_host: Optional[str] = None,
        workdir: str = "/work",
        model: Optional[str] = None,
        max_turns: int = 80,
        cli_path: Optional[str] = None,
        keep_container: bool = False,
        cwd: Optional[str] = None,
        output_dir: Optional[str] = None,
        gpus: Optional[str] = None,
        on_event: Optional[Callable[[ResurrectionEvent], None]] = None,
    ) -> None:
        self.image = image
        self.docker_host = docker_host
        self.workdir = workdir
        self.model = model
        self.max_turns = max_turns
        self.gpus = gpus
        self.cli_path = cli_path or find_claude_cli()
        self.keep_container = keep_container
        # A neutral cwd with no operator files, so the agent can't read host notes.
        self.cwd = cwd or tempfile.mkdtemp(prefix="lazarus-run-")
        # Where emit_contract writes the integration package (on the host).
        self.output_dir = os.path.abspath(output_dir or "lazarus-output")
        self.on_event = on_event
        self.sandbox: Optional[Sandbox] = None

    def _emit(self, kind: str, text: str) -> ResurrectionEvent:
        ev = ResurrectionEvent(kind, text)
        if self.on_event:
            self.on_event(ev)
        return ev

    async def resurrect(self, goal: str) -> ResurrectionResult:
        client = DockerClient(binary=find_docker(), docker_host=self.docker_host)
        sandbox = Sandbox(client, self.image, workdir=self.workdir, gpus=self.gpus)
        sandbox.start()
        self.sandbox = sandbox

        events: list[ResurrectionEvent] = []
        snapshots: list[str] = []
        final_text = ""
        num_turns = 0
        is_error = False
        completed = False

        os.makedirs(self.output_dir, exist_ok=True)
        server, allowed = build_server(sandbox, output_dir=self.output_dir)
        options = ClaudeAgentOptions(
            mcp_servers={SERVER_NAME: server},
            allowed_tools=allowed + ["ToolSearch"],
            disallowed_tools=HOST_TOOLS_BLOCKLIST,
            setting_sources=[],  # don't load host CLAUDE.md / memory / project settings
            cwd=self.cwd,
            system_prompt=SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            max_turns=self.max_turns,
            model=self.model,
            cli_path=self.cli_path,
        )

        try:
            async for msg in query(prompt=goal, options=options):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            final_text = block.text
                            events.append(self._emit("text", block.text))
                        elif isinstance(block, ToolUseBlock):
                            arg_preview = json.dumps(block.input)[:220]
                            events.append(self._emit("tool_use", f"{block.name}({arg_preview})"))
                            if block.name.endswith("sandbox_snapshot"):
                                tag = block.input.get("tag")
                                if tag:
                                    snapshots.append(tag)
                elif isinstance(msg, ToolResultBlock):
                    events.append(self._emit("tool_result", _stringify(msg.content)[:400]))
                elif isinstance(msg, ResultMessage):
                    completed = True
                    num_turns = getattr(msg, "num_turns", 0) or 0
                    is_error = bool(getattr(msg, "is_error", False))
                    events.append(self._emit("result", f"turns={num_turns} error={is_error}"))
        finally:
            if not self.keep_container:
                sandbox.stop()

        return ResurrectionResult(
            completed=completed,
            is_error=is_error,
            final_text=final_text,
            events=events,
            num_turns=num_turns,
            snapshots=snapshots,
            output_dir=self.output_dir,
        )


def _stringify(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", "") or json.dumps(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)
