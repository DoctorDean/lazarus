# Lazarus dashboard — public "try it" surface

A small Starlette app (no new deps beyond what's installed: `starlette`, `uvicorn`,
`httpx`) that demos Lazarus end-to-end: search/enter a GitHub URL → watch it get
resurrected → browse the registry of what's already revived.

```bash
.venv/bin/uvicorn demo.dashboard.app:app --port 8080   # → http://localhost:8080
```

## What's real
- **Registry gallery** — live from `registry/index.json` (the actual revived components).
- **GitHub search** — live GitHub repo-search API; ✓ marks repos we have a recorded run for.
- **Resurrect** — replays the agent's **real** reasoning + shell commands from an actual
  benchmark run, ending on the independently-verified outcome. Nothing is fabricated.

Live resurrection needs the GPU box and takes minutes-to-hours, so the demo replays the
recorded runs instead of launching one live.

## Regenerating the replay data
`traces.json` is baked from the harness stdout logs joined with `results_frame.json`:

```bash
python demo/dashboard/build_traces.py \
    --log <harness_run.out> --log <retry_run.out> \
    --results benchmark/results_frame.json \
    --out demo/dashboard/traces.json
```

Later `--log` files override earlier ones per repo (a resume-retry supersedes the
original failed attempt), so the replay always shows the run that succeeded.
