<!-- Thanks for contributing to Lazarus! Keep this PR focused; link any related issue with "Closes #123". -->

## What & why

<!-- One or two sentences: what this changes and why. -->

## Checklist

- [ ] `pytest -q` passes
- [ ] Focused diff — no unrelated changes
- [ ] No secrets committed (keys live only in a gitignored `.env`)

<!-- If this PR adds or changes a registry tool, also: -->
- [ ] Regenerated the registry (`python scripts/build_registry.py`) so the entry, `index.json`, and docs are in sync
- [ ] The tool actually re-runs from its pinned image and passes its sanity check on a fresh input
- [ ] Licensing respected for any redistributed image (permissive → GHCR; otherwise rebuild-locally, like dMaSIF/Basset)
