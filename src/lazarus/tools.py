"""The Sandbox exposed to Claude as in-process MCP tools.

These are the only hands Lazarus has: everything happens inside the container
through ``sandbox_run`` (a persistent shell), plus targeted file patching,
milestone snapshots, and commit-era dependency pinning. Keeping the tool set
small and container-scoped makes the agent's behaviour legible and safe.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from lazarus.contract import Contract, IOSpec, SmokeCheck, emit
from lazarus.pinner import pin_requirements
from lazarus.sandbox import Sandbox

SERVER_NAME = "lazarus"
TOOL_NAMES = [
    "sandbox_run",
    "sandbox_write_file",
    "sandbox_read_file",
    "sandbox_snapshot",
    "pin_dependencies",
    "emit_contract",
]


def allowed_tool_names() -> list[str]:
    return [f"mcp__{SERVER_NAME}__{name}" for name in TOOL_NAMES]


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def build_server(sandbox: Sandbox, *, output_dir: str, max_output_chars: int = 8000):
    """Build the Lazarus MCP server bound to a live ``sandbox``.

    ``output_dir`` is the host directory where ``emit_contract`` writes the
    integration package. Returns ``(server_config, allowed_tool_names)``.
    """

    @tool(
        "sandbox_run",
        "Run a bash command inside the resurrection sandbox container. State "
        "persists across calls. Returns the exit code and combined stdout+stderr.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "bash command to run"},
                "timeout_s": {"type": "integer", "description": "timeout in seconds (default 600)"},
            },
            "required": ["command"],
        },
    )
    async def sandbox_run(args: dict[str, Any]) -> dict[str, Any]:
        timeout = float(args.get("timeout_s") or 600)
        res = await asyncio.to_thread(sandbox.exec, args["command"], timeout=timeout)
        out = res.combined
        if len(out) > max_output_chars:
            out = f"...[truncated to last {max_output_chars} chars]\n" + out[-max_output_chars:]
        return _text(f"exit_code: {res.exit_code}\n{out}")

    @tool(
        "sandbox_write_file",
        "Write text content to a file path inside the container. Use this to "
        "patch source files (it overwrites the whole file).",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    )
    async def sandbox_write_file(args: dict[str, Any]) -> dict[str, Any]:
        await asyncio.to_thread(sandbox.write_file, args["path"], args["content"])
        return _text(f"wrote {len(args['content'])} bytes to {args['path']}")

    @tool(
        "sandbox_read_file",
        "Read a text file from inside the container.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_bytes": {"type": "integer"},
            },
            "required": ["path"],
        },
    )
    async def sandbox_read_file(args: dict[str, Any]) -> dict[str, Any]:
        max_bytes = int(args.get("max_bytes") or 100_000)
        content = await asyncio.to_thread(sandbox.read_file, args["path"], max_bytes=max_bytes)
        return _text(content)

    @tool(
        "sandbox_snapshot",
        "docker commit the current container to an image tag, banking an "
        "expensive successful milestone so a later failure doesn't cost the build.",
        {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "image tag, e.g. lazarus/masif:site-ready"},
                "message": {"type": "string"},
            },
            "required": ["tag"],
        },
    )
    async def sandbox_snapshot(args: dict[str, Any]) -> dict[str, Any]:
        tag = await asyncio.to_thread(sandbox.snapshot, args["tag"], message=args.get("message"))
        return _text(f"snapshotted container to image: {tag}")

    @tool(
        "pin_dependencies",
        "Resolve Python packages to the newest versions that existed on PyPI on "
        "or before a cutoff date (the repo's commit era). Use when pip installs "
        "the wrong, too-new versions.",
        {
            "type": "object",
            "properties": {
                "commit_date": {"type": "string", "description": "YYYY-MM-DD"},
                "packages": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["commit_date", "packages"],
        },
    )
    async def pin_dependencies(args: dict[str, Any]) -> dict[str, Any]:
        cutoff = datetime.strptime(args["commit_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        pinned = await asyncio.to_thread(pin_requirements, args["packages"], cutoff)
        lines = [
            f"{name}=={ver}" if ver else f"# {name}: no release on/before {args['commit_date']}"
            for name, ver in pinned.items()
        ]
        return _text("\n".join(lines))

    @tool(
        "emit_contract",
        "Emit the final integration contract as a self-contained package (lazarus.yaml, "
        "Dockerfile, predict.py, smoke_test.py). Call this ONCE at the end, after you have "
        "a working minimal command and a passing sanity check. entrypoint is a bash template "
        "using $INPUT (the input file) and $OUTDIR (where outputs go).",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "capability id, e.g. masif_site"},
                "base_image": {"type": "string", "description": "the snapshotted image tag to call"},
                "entrypoint": {"type": "string", "description": "bash template using $INPUT and $OUTDIR"},
                "repo_url": {"type": "string"},
                "commit": {"type": "string"},
                "paper": {"type": "string"},
                "inputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["name", "type"],
                    },
                },
                "outputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["name", "type"],
                    },
                },
                "smoke": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "command": {"type": "string", "description": "in-container command printing <metric>=<value>"},
                        "metric": {"type": "string"},
                        "threshold": {"type": "number"},
                        "input_ref": {"type": "string"},
                    },
                    "required": ["description", "command"],
                },
                "patches": {"type": "array", "items": {"type": "string"}},
                "gpus": {"type": "string", "description": "set to 'all' if the method needs a GPU — makes the emitted package pass --gpus"},
            },
            "required": ["name", "base_image", "entrypoint"],
        },
    )
    async def emit_contract(args: dict[str, Any]) -> dict[str, Any]:
        smoke = args.get("smoke")
        contract = Contract(
            name=args["name"],
            repo_url=args.get("repo_url", ""),
            base_image=args["base_image"],
            entrypoint=args["entrypoint"],
            inputs=[IOSpec(**i) for i in args.get("inputs", [])],
            outputs=[IOSpec(**o) for o in args.get("outputs", [])],
            smoke=SmokeCheck(**smoke) if smoke else None,
            paper=args.get("paper", ""),
            commit=args.get("commit", ""),
            patches=args.get("patches", []),
            gpus=args.get("gpus", ""),
        )
        out = await asyncio.to_thread(emit, contract, output_dir)
        written = ", ".join(sorted(p.name for p in out.iterdir()))
        return _text(f"wrote integration contract to {out}\nfiles: {written}")

    server = create_sdk_mcp_server(
        name=SERVER_NAME,
        version="0.1.0",
        tools=[
            sandbox_run, sandbox_write_file, sandbox_read_file,
            sandbox_snapshot, pin_dependencies, emit_contract,
        ],
    )
    return server, allowed_tool_names()
