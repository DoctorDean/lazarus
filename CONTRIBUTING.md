# Contributing to Lazarus

Thanks for wanting to help bring dead research code back to life. 🧬

Lazarus turns unrunnable research repos into callable, verified components. The most
valuable contributions grow the set of revived tools and make the revival engine more
robust. There are three ways in — pick whichever fits.

---

## Ways to contribute

### 1. Add a revived tool to the registry  ← the highest-leverage contribution
You resurrected a repo (with `lazarus resurrect <url>`, or by hand) and want others to reuse
it. A registry entry is the curated metadata a contract doesn't carry — title, domain, era,
one-line summary, license, the sanity check it passed, and where its image lives.

The curated entries are defined as `RegistryEntry(...)` objects in
[`scripts/build_registry.py`](scripts/build_registry.py). To add one:

1. Append a `RegistryEntry(...)` to the `ENTRIES` list. Copy an existing entry and fill in:
   - `name` (unique slug), `title`, `domain`, `summary`, `repo_url`, `paper`, `era`, `license`
   - `base_image` — the container image (see [Images](#images-ghcr) below)
   - `gpu` — `True` if it needs a GPU
   - `sanity_metric` / `sanity_threshold` / `sanity_direction` — the falsifiable check it passes
   - `reproduced_*` — only if it matched the paper's own number
   - `contract` — path to the contract bundle (module + CLI + smoke test)
   - `giveback_pr` — link if you upstreamed the fix; else omit
2. Regenerate the published artifacts:
   ```bash
   python scripts/build_registry.py     # writes registry/entries/*.yaml + index.json + docs/registry.md
   ```
3. Run the tests (`pytest -q`) and open a PR.

**Bar for inclusion:** the tool must actually run and pass its own sanity check, on a fresh
input, from the pinned image — not "it built once on my laptop." A revival that can't be
independently re-run isn't ready for the registry (but *is* a great harness bug report — see #2).

### 2. Improve the revival engine / report a revival that failed
Found a repo Lazarus couldn't revive, or a decay pattern it mishandled? That's gold — it's
how the engine gets better. Open an issue with the repo URL and the failure (the harness's
reason-code + log tail if you have it). PRs that harden the Scout, the pinner, the repair
loop, or the sandbox are very welcome. See the benchmark harness in
[`benchmark/`](benchmark/) for how outcomes are classified and verified.

### 3. Give back to the original authors
When Lazarus finds a real fix (a rotted URL, a broken path, a decades-old UB bug), it can
become a maintainer-ready PR to the source repo with a CI smoke test so it can't silently rot
again. See [`giveback/`](giveback/) for examples. Respect each repo's license — some (e.g.
no-derivatives) preclude redistribution; upstream a patch instead.

---

## Development setup

```bash
git clone https://github.com/DoctorDean/lazarus && cd lazarus
python -m venv .venv && source .venv/bin/activate     # or: uv venv
pip install -e ".[dev,agent]"                         # agent extras need Python ≥ 3.10 + Docker

# the agent loop needs Claude auth — log in the `claude` CLI, or:
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env            # .env is gitignored; never commit keys
```

Run the tests:
```bash
pytest -q                 # the pure logic (registry, benchmark classifier, report) — no Docker needed
```

Where things run is pluggable via one flag — a local container, a remote x86 box, or a GPU
rental — through `--docker-host` / `DOCKER_HOST` (e.g. `ssh://you@gpu-box`). Only tasks that
actually resurrect or execute a component need Docker; the unit tests don't.

## Branches

- **`main`** — stable, what people install and pull from. Keep it green.
- **`next`** — active development. Branch from `next`, PR back into `next`. Maintainers
  promote `next` → `main` when a batch is ready.

## Images (GHCR)

Revived tools are backed by a pinned container image, distributed via **GitHub Container
Registry** (`ghcr.io/doctordean/lazarus-<name>`). If you're adding a tool, see
[`docs/IMAGES.md`](docs/IMAGES.md) for how to publish its image and set `base_image`. Only
publish images whose upstream license permits redistribution — when in doubt, ship the
contract + recipe and let Lazarus rebuild the image locally.

## Pull-request checklist

- [ ] `pytest -q` passes
- [ ] New registry entry regenerated via `scripts/build_registry.py` (entry + index + docs in sync)
- [ ] Any revived tool actually re-runs from its pinned image and passes its sanity check
- [ ] No secrets committed (keys live only in a gitignored `.env`)
- [ ] Licensing respected for any redistributed image or upstreamed patch

## Code style

Match the surrounding code — it favors small, well-commented functions and clear names over
cleverness. Comments explain *why*, not *what*. Keep diffs focused.

## Questions

Open an issue or start a discussion. First time? Look for issues labelled `good first issue` —
adding a registry entry for a tool you've revived is a great one.
