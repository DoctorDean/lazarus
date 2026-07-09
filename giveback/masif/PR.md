# PR: Fix rotted PDB download (#85) + add a CI smoke test

**Title:** Fix broken PDB download in `00-pdb_download.py` (#85) and add a MaSIF-site CI smoke test

**Target:** `LPDI-EPFL/masif` — base branch `master`

---

## What this fixes

`source/data_preparation/00-pdb_download.py` downloads structures via Biopython's
`PDBList.retrieve_pdb_file(...)`, which relies on legacy wwPDB download paths that RCSB
has since retired. It now fails silently — no file is written — and the whole
`data_prepare_one.sh` pipeline then dies downstream with a confusing "structure doesn't
exist" / `IndexError`. This is the root cause behind **#85** (and the symptoms in #83).

**The fix** is a two-line change: fetch the structure directly from the current, stable
RCSB endpoint (`https://files.rcsb.org/download/<ID>.pdb`) instead of going through
Biopython's retired path. It's Python 2/3 compatible and needs no new dependencies.

## Verification

Ran the canonical example end-to-end on the published `pablogainza/masif:latest` image
with **only** this change (no `--file` workaround):

```
./data_prepare_one.sh 4ZQK_A     # built-in download — now works again
./predict_site.sh 4ZQK_A
./color_site.sh 4ZQK_A
# -> ROC AUC score for protein 4ZQK_A : 0.9137
```

That matches the value in the paper, so the whole interaction-site path is healthy again.

## Also included: a CI smoke test

`.github/workflows/masif-site-smoke.yml` runs exactly the above on every push/PR (inside
the published image) and asserts the 4ZQK_A ROC-AUC stays ≥ 0.8. The repo currently has
no CI, which is why the download breakage went unnoticed for years — this gives MaSIF a
reproducibility heartbeat so it can't silently rot again.

## Changes

- `source/data_preparation/00-pdb_download.py` — direct RCSB fetch (the fix)
- `.github/workflows/masif-site-smoke.yml` — new CI smoke test

---

*Full disclosure: the diagnosis and fix were produced with an automated repo-resurrection
agent and then verified by hand end-to-end (the ROC-AUC above is a real run). Happy to
adjust anything to fit the project's conventions.*
