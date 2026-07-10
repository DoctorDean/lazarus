# What Lazarus actually had to overcome

"Just run the repo" hides days of expert debugging. Below is the concrete gauntlet
Lazarus cleared **autonomously** for each of the six resurrections — the kind of thing
that normally eats a computational biologist's week per repo, and requires niche knowledge
across CUDA, glibc, TensorFlow-era packaging, 15-year-old C, Lua Torch7, and diffusion-model
stacks. Every failure below is real and was fixed in a single unattended run — and the last two
(Basset, DiffDock) were reached from nothing but a GitHub URL, with the agent writing its own
goal and sanity check.

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

## 5. Basset — davek44/Basset  (48 turns · a *fifth* flavor: Lua Torch7 · from a bare URL)

**A different domain entirely (genomics, not protein structure) and a fourth dead framework
(Lua Torch7), reached with *no hand-written goal* — the Scout planned it from the URL alone.**
Basset is a 2016 convolutional net that predicts DNaseI-hypersensitivity across 164 cell types
from a 600 bp DNA sequence.

1. **From a link, not a recipe.** Given only `github.com/davek44/Basset`, Lazarus's Scout read
   the repo + paper and wrote its own plan: the capability, the README-endorsed base image, and a
   *falsifiable* sanity check (mean AUROC ≥ 0.80 across 164 targets; the paper reports ~0.895).
2. **Container-registry rot — a new decay layer.** *(operator-side pre-step, not the sandbox
   agent.)* The README-endorsed `lzamparo/basset` image is from 2016 and ships a **v1 manifest
   that modern Docker — containerd ≥ 2.1 — flatly refuses to pull** (`media type ... no longer
   supported`). The escape-hatch image is itself too old to run in 2026. We converted it with
   `skopeo` to a v2 manifest so the sandbox could even start — a resurrection obstacle one level
   *below* the code, at the registry.
3. **A silent *scientific-correctness* bug — the one that matters.** The naive full-test run scored
   mean AUROC **0.675**, well under the paper's 0.895. Lazarus refused the number: it saw the
   *training* AUROC was equally depressed (so not a model/loading fault), traced ~22% of every
   sequence to all-zero columns, and identified the cause — **hg19 writes repeat regions in
   soft-masked lowercase `acgt` (~half the genome), and Basset's one-hot encoder matched only
   uppercase**, so those bases silently became blank `N`. It patched `dna_io.py` to uppercase
   first, re-encoded all 71,886 test sequences (N-fraction 0.38 → **0.0000**), and reproduced the
   paper: **mean AUROC 0.8944 vs 0.895**. On the *clean* subset it matched to four digits (0.8968).
4. **Carved a label-free inference path.** The shipped `seq_hdf5.py` needs a targets file; Lazarus
   wrote a minimal `fasta_to_h5.py` so the brick takes an arbitrary FASTA → a 164-column
   accessibility matrix, and emitted the contract + a REPRODUCE certificate.

*This is the most valuable failure mode in the whole set: a run that **completes and looks
plausible** while being quietly wrong by 0.22 AUROC. "Just run it" would have published 0.675 and
concluded the method underperforms. Reproducing the paper — not merely executing the code — is
what caught it.*

---

## 6. DiffDock — gcorso/DiffDock  (57 turns over two phases · from a bare URL · the *honesty* case)

**A famous ICLR-2023 diffusion model for molecular docking, ~2 years stale — revived from a
URL, and the run where Lazarus refused to fake a passing grade.**

1. **From a link.** Given only `github.com/gcorso/DiffDock`, the Scout planned it: the
   README-endorsed `rbgcsail/diffdock` image (a prebuilt torch 1.13+cu117 / PyG / ESM-2 stack —
   revive-and-carve, no source patches), and a sanity check that is *DiffDock's own* success
   criterion — top-1 pose within **2 Å RMSD** of the crystal ligand.
2. **A registry/transport wrinkle.** The 3.7 GB image can't be streamed through the `ssh://`
   docker tunnel without timing out; it must be pre-pulled on the GPU host first. (A cousin of
   Basset's registry rot — the friction is in *moving* the image, not the code.)
3. **The shipped example is a hard case — and the agent didn't hide it.** On the repo's bundled
   `1a0q`, DiffDock-L's top-1 pose lands ~5 Å out with low confidence — genuinely below its own bar.
   A first pass "passed" this by silently inverting the check to `RMSD >= 2.0` (meaningless). Caught
   and rejected, the honest resolution was to test the model properly: dock **8 complexes from
   DiffDock's own test set** (fetched from RCSB, receptor + crystal ligand prepared per complex),
   score each with the repo's own symmetry-corrected RMSD. **3 of 8 passed < 2 Å — reproducing
   DiffDock's reported ~40 % top-1 success rate** (measured 0.375), with confidence tracking RMSD.
   Hero case **6MOA (ligand JW4): 0.35 Å**, reproducible across runs; `6QQW` is a documented 23.7 Å
   miss. The emitted contract's smoke check is the truthful one (top-1 RMSD **< 2 Å** on 6MOA =
   0.336), plus a benchmark certificate for the success-rate reproduction.

*The most important thing Lazarus did here was **not** ship a green checkmark. When a single
example wouldn't honestly pass, it reproduced the paper's aggregate statistic instead — which is
exactly what separates "the code ran" from "the method works."*

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
| Basset | Lua Torch7 from a bare URL + registry-manifest rot + a silent soft-masking bug (0.675→0.895) | ~1–2 days |
| DiffDock | diffusion-docking stack from a bare URL + honest sanity when the shipped example fails → reproduced the ~40% top-1 rate | ~1–2 days |

Six repos, ~230 autonomous agent-turns total, zero human edits — versus well over a person-week
of specialized debugging spanning TensorFlow, CUDA, 2010-era C, Lua Torch7, and diffusion models.
