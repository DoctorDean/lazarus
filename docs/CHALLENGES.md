# What Lazarus actually had to overcome

"Just run the repo" hides days of expert debugging. Below is the concrete gauntlet
Lazarus cleared **autonomously** for each of the four resurrections — the kind of thing
that normally eats a computational biologist's week per repo, and requires niche knowledge
across CUDA, glibc, TensorFlow-era packaging, and 15-year-old C. Every failure below is
real and was fixed in a single unattended run.

---

## 1. MaSIF — LPDI-EPFL/masif  (18 turns · ROC-AUC 0.9137)

**The stack that no longer resolves:** Python 3.6, TensorFlow 1.12, a *from-source* PyMesh
build, and an external-binary chain (MSMS, APBS, PDB2PQR, `reduce`) invoked through slurm
shell scripts. None of it `pip install`s in 2026.

What Lazarus had to figure out:
1. **Don't rebuild — revive.** It recognized the published `pablogainza/masif` image bakes
   the entire binary chain, and pivoted to a "revive-and-carve" strategy instead of fighting
   PyMesh-from-source (a multi-hour dead end on its own).
2. **The silent-killer download bug (issue #85).** `00-pdb_download.py` calls Biopython's
   `PDBList.retrieve_pdb_file`, which depends on legacy wwPDB paths RCSB retired. It fails
   **silently** — no file, no error — then dies pages later with a confusing `IndexError`.
   Lazarus traced the empty-list symptom back to the dead download and routed around it.
3. **Three separate CPU-architecture landmines.** On Apple-silicon emulation it discovered,
   by *running* them: TensorFlow aborts fatally (`SIGABRT`) because the wheel needs **AVX**
   that Rosetta doesn't provide; **MSMS `SIGILL`s** (illegal instruction) on real geometry;
   and `reduce` is a **32-bit i386** binary Rosetta can't run at all. It correctly concluded
   this is an *environmental* blocker no in-sandbox fix can solve, and escalated to a native-x86
   host — exactly the right call.
4. **Carve the capability.** It located `predict_site` inside the script maze and extracted a
   minimal PDB → per-vertex-score path, skipping the ~400 GB slurm training data-prep.

*A human would need working knowledge of Rosetta's AVX/32-bit gaps, MSMS's quirks, RCSB's
endpoint history, and MaSIF's undocumented script graph — and would still lose a day to the
silent download bug alone.*

---

## 2. ScanNet — jertubiana/ScanNet  (19 turns · ROC-AUC 0.9233)

**Stack:** Python 3.6, TensorFlow 1.14 + standalone Keras 2.2.5 (not `tf.keras`).

1. **`library_folder = ''` (issue #15).** Every path (`structures_folder`, `predictions_folder`,
   `model_folder`, `MSA_folder`) resolves relative, so inference fails off the repo root —
   and `--noMSA` still trips the MSA path. Lazarus set it correctly and created the dirs.
2. **A second dead endpoint (issue #14).** The downloader targets `mmtf.rcsb.org` — which RCSB
   **shut down** — so fetching by ID returns `None` → `NoneType` crash. It sidestepped with a
   local file.
3. **It wrote its own ground truth.** No labels ship for a single PDB, so Lazarus authored a
   Biopython + scikit-learn evaluation from scratch — interface residues within 5 Å of the
   partner chain, then residue-level ROC-AUC — to actually *prove* the revival.

*Different framework, different failure modes — proof the agent isn't replaying a MaSIF recipe.*

---

## 3. dMaSIF — FreyrS/dMaSIF  (51 turns · ROC-AUC 0.8390 · the hardest)

**No Docker image. Build the whole GPU stack from a bare image — and PyKeOps is a minefield.**

1. **The README stack is dead-on-arrival.** Its CUDA-10 / PyKeOps-1.4 recipe **cannot target
   the A4500** (Ampere, compute capability sm_86, which needs CUDA ≥ 11.1). Lazarus reasoned to
   a working `torch==1.8.1+cu111` stack with the four version-locked PyTorch-Geometric wheels.
2. **The KeOps `cppyy` / glibc trap.** The `python_engine` branch imports `cppyy` unconditionally;
   **no `cppyy` wheel exists for the base image's glibc 2.27**, and `cppyy-cling` fails to build.
   Lazarus worked out that released **`pykeops 2.1.2`** dropped `cppyy` for a `ctypes`+NVRTC
   binder with the *same* `LazyTensor` API — and **overrode the build guidance it was given**
   because it found a genuinely better path under the real constraint. That is engineering, not
   instruction-following.
3. **The weights aren't in the repo (issue #35).** The FreyrS repo ships only the *search*
   model; the *site* weights live in a community fork (`casperg92/MaSIF_colab`). Lazarus located
   and used them.
4. **Transitive-dependency archaeology.** It pinned `numpy` back down (the PyG install pulled
   1.24, which removed `np.float` and breaks the era's code) and `googledrivedownloader==0.4`
   (module-name change) — the exact commit-era reasoning that keeps old stacks alive.
5. **A source-level GPU bug — and an *improvement*.** `geometry_processing.py::soft_distances`
   used `torch.FloatTensor([...], device=cuda)`; the legacy constructor rejects a CUDA device,
   which is precisely why the original Colab **forced everything to CPU**. Lazarus patched it to
   `torch.tensor(..., device=x.device)` — **unlocking GPU execution the original could not do.**

*This is a genuine research-engineer's day (or three): CUDA/Ampere compatibility, the KeOps 1.x→2.x
history, glibc ABI limits, finding weights in a fork, and a CUDA tensor-construction bug.*

---

## 4. fpocket — 2010 SourceForge release  (32 turns · a different flavor: C)

**Not Python, not CUDA — a 15-year-old C program built against a 2026 toolchain.**

1. **Download evasion.** SourceForge's `/download` serves a JavaScript interstitial, not the
   tarball. Lazarus extracted the fresh `ts=` token and re-requested **with a `Referer` header**
   to get the real 5.4 MB gzip.
2. **Modern-GCC breakage.** GCC 13/14 promote `-Werror=implicit-function-declaration` /
   `implicit-int` to hard errors, which 2010 C trips. It applied the right escape-hatch flags
   (`-std=gnu89 -Wno-error=...`) and built only the `fpocket` target (skipping `mdpocket`/netcdf).
3. **Link-order break.** Modern `ld` is order-sensitive; `-lm` sat *before* the objects →
   `undefined reference`. Lazarus patched the makefile to move it after.
4. **A 15-year-old undefined-behavior bug.** `sprintf(out_path, "%s/%s", out_path, ...)` writes a
   buffer into itself — overlapping source/dest, technically UB. It happened to work on 2010's
   glibc and **silently corrupts to empty on modern glibc**, so every output path collapsed to
   `/pockets` and no results were written. Lazarus read `fpout.c`, pinned the two offending
   `sprintf`s, and rewrote them with a scratch buffer.

*Latent UB exposed by a decade of glibc changes is exactly the kind of bug that makes people give
up on old scientific binaries. Lazarus found it by disassembling the failure, not by luck.*

---

## The cross-cutting infrastructure problem

Three of the four have binaries that **cannot run under Apple-silicon emulation** (AVX-only
TensorFlow, `SIGILL`ing MSMS, 32-bit `reduce`, an Ampere-only GPU model). Lazarus's sandbox is
**host-pluggable**: it drove every run from a MacBook and executed on a native-x86 + GPU
workstation over a single `--docker-host ssh://` flag — and knew *when* to escalate there rather
than spin on an unwinnable local fix.

## Bottom line

| Repo | Signature challenge | Realistic human effort |
|---|---|:--:|
| MaSIF | AVX/SIGILL/32-bit emulation walls + silent download death | ~1 day |
| ScanNet | two dead endpoints + writing the eval from scratch | ~half a day |
| dMaSIF | GPU build from scratch, KeOps/cppyy/glibc, weights-in-a-fork, a CUDA source patch | ~2–3 days |
| fpocket | download evasion + modern-GCC/ld + a 15-yr UB bug | ~half–1 day |

Four repos, ~120 autonomous agent-turns total, zero human edits — versus roughly a person-week
of specialized debugging.
