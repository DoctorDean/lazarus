# Registry

A living archive of tools Lazarus has brought back from the dead — each revived
from its source repo into a callable, containerised brick with a verified sanity
check, and (where a benchmark exists) a reproduced paper number.

**6 revived tools.** Pull any of them: `lazarus pull <name>`.

| Tool | Domain | Era / stack | Result | From a URL |
|---|---|---|---|:--:|
| **Basset** | Genomics — chromatin accessibility | 2016 · Lua Torch7 | **0.894 vs 0.895** (mean AUROC (164 targets)) | ✅ |
| **DiffDock** | Molecular docking | 2023 · PyTorch diffusion · ESM-2 · GPU | **0.375 vs 0.4** (top-1 success rate (<2Å)) | ✅ |
| **dMaSIF** | Protein interface (surface, GPU) | 2021 · Py3.6 · torch cu111 · PyKeOps · GPU | smoke ROCAUC ≥ 0.65 | — |
| **fpocket** | Druggable pocket detection | 2010 C · built on modern GCC | smoke pockets ≥ 1 | — |
| **MaSIF-site** | Protein interaction sites | 2020 · Py3.6 · TF 1.12 · MSMS/APBS | **0.82 vs 0.85** (median ROC-AUC) | — |
| **ScanNet** | Protein binding sites | 2022 · Py3.6 · TF 1.14 · Keras | smoke ROC_AUC ≥ 0.7 | — |

---

## Basset  <small>`basset_predict`</small>

Predict DNaseI-hypersensitivity across 164 cell types from a 600 bp DNA sequence.

- **Source:** [davek44/Basset](https://github.com/davek44/Basset) · see source repo
- **Stack:** 2016 · Lua Torch7
- **Sanity check:** `min_perseq_std ≥ 0.01`  ·  **reproduced the paper:** mean AUROC (164 targets) **0.894** vs 0.895
- **Revived:** 48 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Kelley et al., Genome Research 2016 — Basset

```bash
lazarus pull basset_predict
```

> ℹ️ The pinned image `lazarus/basset:site-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## DiffDock  <small>`diffdock_blind_docking`</small>

Blind docking — protein + ligand → ranked, confidence-scored 3D poses (diffusion model).

- **Source:** [gcorso/DiffDock](https://github.com/gcorso/DiffDock) · MIT
- **Stack:** 2023 · PyTorch diffusion · ESM-2 · GPU  ·  GPU
- **Sanity check:** `rmsd < 2.0`  ·  **reproduced the paper:** top-1 success rate (<2Å) **0.375** vs 0.4
- **Revived:** 57 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Corso et al., ICLR 2023 — DiffDock

```bash
lazarus pull diffdock_blind_docking
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-diffdock:site-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## dMaSIF  <small>`dmasif_site`</small>

Differentiable molecular-surface interface prediction, built and run on GPU.

- **Source:** [FreyrS/dMaSIF](https://github.com/FreyrS/dMaSIF) · CC BY-NC-ND
- **Stack:** 2021 · Py3.6 · torch cu111 · PyKeOps · GPU  ·  GPU
- **Sanity check:** `ROCAUC ≥ 0.65`
- **Revived:** 51 autonomous agent-turns
- **Paper:** Sverrisson et al., CVPR 2021 — dMaSIF

```bash
lazarus pull dmasif_site
```

> ℹ️ The pinned image `lazarus/dmasif:site-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## fpocket  <small>`fpocket2`</small>

Detect and rank druggable pockets on a protein structure (Voronoi / alpha-spheres).

- **Source:** [https://fpocket.sourceforge.net](https://fpocket.sourceforge.net) · MIT
- **Stack:** 2010 C · built on modern GCC
- **Sanity check:** `pockets ≥ 1`
- **Revived:** 32 autonomous agent-turns
- **Paper:** Le Guilloux et al., BMC Bioinformatics 2009 — fpocket

```bash
lazarus pull fpocket2
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-fpocket:working` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## MaSIF-site  <small>`masif_site`</small>

Predict per-residue protein-interaction-site probability from a molecular surface.

- **Source:** [LPDI-EPFL/masif](https://github.com/LPDI-EPFL/masif) · Apache-2.0
- **Stack:** 2020 · Py3.6 · TF 1.12 · MSMS/APBS
- **Sanity check:** `roc_auc ≥ 0.8`  ·  **reproduced the paper:** median ROC-AUC **0.82** vs 0.85
- **Revived:** 18 autonomous agent-turns
- **Given back:** [masif PR #93](https://github.com/LPDI-EPFL/masif/pull/93)
- **Paper:** Gainza et al., Nature Methods 2020 — MaSIF

```bash
lazarus pull masif_site
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-masif:site-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## ScanNet  <small>`scannet_ppi_binding_sites`</small>

Per-residue protein–protein binding-site probability from one structure (structure-only, no MSA).

- **Source:** [jertubiana/ScanNet](https://github.com/jertubiana/ScanNet) · Apache-2.0
- **Stack:** 2022 · Py3.6 · TF 1.14 · Keras
- **Sanity check:** `ROC_AUC ≥ 0.7`
- **Revived:** 19 autonomous agent-turns
- **Given back:** [ScanNet PR #16](https://github.com/jertubiana/ScanNet/pull/16)
- **Paper:** Tubiana et al., Nature Methods 2022 — ScanNet

```bash
lazarus pull scannet_ppi_binding_sites
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-scannet:ppi-noMSA-proven` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.
