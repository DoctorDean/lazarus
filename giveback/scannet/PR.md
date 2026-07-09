# PR: Fix single-PDB prediction with unset `library_folder` (#15) + add CI

**Title:** Make `library_folder` auto-detect the repo location (fixes #15) and add a CI smoke test

**Target:** `jertubiana/ScanNet` — base branch `main`

---

## What this fixes (#15)

`utilities/paths.py` ships with `library_folder = ''`, so `structures_folder`,
`predictions_folder`, `model_folder`, and `MSA_folder` all resolve to **bare relative
paths**. Unless you run from exactly the repo root, prediction fails trying to read/write
those folders — this is the root cause of **#15** (`--noMSA` still trips over the paths).

**The fix** makes `library_folder` auto-detect the repo location from the file's own path,
so it's correct no matter where you invoke ScanNet from:

```diff
- library_folder = '' # Where the Github Repo is located.
+ import os
+ library_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'  # auto-detect repo root
```

(`paths.py` lives in `utilities/`, so this resolves to the repo root.) Users can still
override it by editing the line, exactly as before.

## Verification

With only this change, ran single-PDB interface prediction **from a different working
directory**, structure-only, using the shipped weights:

```
cd /tmp
python /ScanNet/predict_bindingsites.py /tmp/4ZQK.pdb_A --noMSA
# -> "prediction done!"  ->  predictions/4ZQK_(0-A)_single_ScanNet_interface_noMSA/predictions_4ZQK.csv
```

## Also included: a CI smoke test

`.github/workflows/scannet-smoke.yml` runs the above on every push/PR inside the published
`jertubiana/scannet` image and asserts a prediction CSV is produced — a reproducibility
heartbeat for the single-PDB path.

## Related, not fixed here (#14)

The auto-downloader in `preprocessing/PDBio.py` targets `mmtf.rcsb.org` (which RCSB has
**shut down**) and legacy wwPDB paths, so downloading by ID fails with "File not found"
(**#14**). The reliable workaround today is to pass a **local structure file**
(`/path/to/file.pdb_A`), which is what the CI does. Happy to follow up with a downloader
fix (fetch from `https://files.rcsb.org/download/`) if you'd like it in the same PR.

## Changes

- `utilities/paths.py` — auto-detect `library_folder` (the fix)
- `.github/workflows/scannet-smoke.yml` — new CI smoke test

---

*Full disclosure: diagnosis and fix were produced with an automated repo-resurrection
agent and verified by hand (the run above is real). Glad to adjust to fit conventions.*
