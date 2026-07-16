#!/usr/bin/env python3
"""Lazarus — public "try it" dashboard (Starlette + SSE, no extra deps).

    uvicorn demo.dashboard.app:app --port 8080     # or: python demo/dashboard/app.py

Surfaces three real pieces of Lazarus:
  •  the registry of already-revived, callable components  (registry/index.json)
  •  GitHub repo search, so you can find a URL to point it at  (live GitHub API)
  •  "Resurrect" — streams the agent's REAL recorded reasoning + shell commands for
     a repo we've actually revived, ending on the independently-verified outcome
     (demo/dashboard/traces.json, baked from the benchmark run).

The replay is honest: every step is the agent's actual output from a real run — no
fabricated results. Live resurrection needs the GPU box and takes minutes-to-hours,
so the demo replays recorded runs instead of competing for it.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry" / "index.json"
TRACES = HERE / "traces.json"


def _load_json(p: Path, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _traces() -> dict:
    return _load_json(TRACES, {})


# ------------------------------------------------------------------ routes ---
async def index(_: Request) -> HTMLResponse:
    return HTMLResponse((HERE / "index.html").read_text())


async def api_registry(_: Request) -> JSONResponse:
    data = _load_json(REGISTRY, {"entries": []})
    return JSONResponse(data.get("entries", []))


async def api_catalog(_: Request) -> JSONResponse:
    """The repos the demo can actually resurrect (real recorded runs), slim cards."""
    cards = [{
        "repo_url": t["repo_url"], "name": t["name"], "outcome": t["outcome"],
        "turns": t.get("turns"), "wall_clock_s": t.get("wall_clock_s"),
        "cost_usd": t.get("cost_usd"), "steps": len(t.get("steps", [])),
        "reproduced_measured": t.get("reproduced_measured"),
        "reproduced_reported": t.get("reproduced_reported"),
    } for t in _traces().values()]
    cards.sort(key=lambda c: (c["outcome"] != "reproduced", c["name"].lower()))
    return JSONResponse(cards)


async def api_search(request: Request) -> JSONResponse:
    """Live GitHub repo search. Marks results we can resurrect in this demo."""
    q = (request.query_params.get("q") or "").strip()
    if not q:
        return JSONResponse([])
    have = set(_traces().keys())
    url = "https://api.github.com/search/repositories"
    params = {"q": q, "per_page": "10", "sort": "stars", "order": "desc"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params,
                                 headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            items = r.json().get("items", [])
    except (httpx.HTTPError, ValueError) as exc:
        return JSONResponse({"error": f"GitHub search unavailable: {exc}"}, status_code=502)
    out = [{
        "full_name": it["full_name"], "repo_url": it["html_url"],
        "description": it.get("description") or "", "stars": it.get("stargazers_count", 0),
        "language": it.get("language") or "", "pushed_at": (it.get("pushed_at") or "")[:10],
        "resurrectable": it["html_url"] in have,
    } for it in items]
    # surface anything we can actually resurrect to the top
    out.sort(key=lambda c: (not c["resurrectable"], -c["stars"]))
    return JSONResponse(out)


def _sse(obj: dict) -> bytes:
    return f"data: {json.dumps(obj)}\n\n".encode()


async def api_resurrect(request: Request) -> StreamingResponse:
    """Replay a real recorded resurrection as a Server-Sent-Events stream."""
    repo_url = (request.query_params.get("url") or "").strip()
    trace = _traces().get(repo_url)

    async def gen():
        if not trace:
            yield _sse({"phase": "error",
                        "text": "Not in the demo corpus — pick a ✓ resurrectable repo "
                                "(a live run needs the GPU box and takes minutes)."})
            return
        steps = trace.get("steps", [])
        yield _sse({"phase": "scout", "name": trace["name"], "repo_url": repo_url,
                    "total": len(steps),
                    "text": f"Scouting {trace['name']} — reading the repo + paper to draft a plan…"})
        await asyncio.sleep(0.6)
        # pace so even a 90-step trace replays in ~15s but short ones still feel live
        delay = max(0.08, min(0.32, 14.0 / max(1, len(steps))))
        for i, s in enumerate(steps, 1):
            await asyncio.sleep(delay)
            yield _sse({"phase": "step", "i": i, "total": len(steps),
                        "kind": s["kind"], "text": s["text"], "detail": s.get("detail", "")})
        await asyncio.sleep(0.4)
        yield _sse({"phase": "done",
                    "outcome": trace["outcome"], "turns": trace.get("turns"),
                    "wall_clock_s": trace.get("wall_clock_s"), "cost_usd": trace.get("cost_usd"),
                    "verified": trace.get("verified"), "summary": trace.get("summary"),
                    "sanity_metric": trace.get("sanity_metric"),
                    "sanity_threshold": trace.get("sanity_threshold"),
                    "reproduced_measured": trace.get("reproduced_measured"),
                    "reproduced_reported": trace.get("reproduced_reported")})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


app = Starlette(routes=[
    Route("/", index),
    Route("/api/registry", api_registry),
    Route("/api/catalog", api_catalog),
    Route("/api/search", api_search),
    Route("/api/resurrect", api_resurrect),
])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
