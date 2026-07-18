# Registry

A living archive of tools Lazarus has brought back from the dead — each revived
from its source repo into a callable, containerised brick with a verified sanity
check, and (where a benchmark exists) a reproduced paper number.

**11 revived tools.** Pull any of them: `lazarus pull <name>`.

| Tool | Domain | Era / stack | Result | From a URL |
|---|---|---|---|:--:|
| **Basset** | Genomics — chromatin accessibility | 2016 · Lua Torch7 | **0.894 vs 0.895** (mean AUROC (164 targets)) | ✅ |
| **CoCoNet** | Viral metagenome binning | 2021 · Python · PyTorch | smoke n_contigs_assigned ≥ 9 | ✅ |
| **DeepLatentMicrobiome** | Microbiome — environment → OTUs | 2021 · Python · TF/Keras | **0.7368 vs 0.739** (mean per-sample Pearson r (n=373)) | ✅ |
| **DiffDock** | Molecular docking | 2023 · PyTorch diffusion · ESM-2 · GPU | **0.375 vs 0.4** (top-1 success rate (<2Å)) | ✅ |
| **dMaSIF** | Protein interface (surface, GPU) | 2021 · Py3.6 · torch cu111 · PyKeOps · GPU | smoke ROCAUC ≥ 0.65 | — |
| **DnaFeaturesViewer** | Sequence annotation plots | Python · Biopython · matplotlib | smoke feature_count ≥ 10 | ✅ |
| **fpocket** | Druggable pocket detection | 2010 C · built on modern GCC | smoke pockets ≥ 1 | — |
| **HiTEA** | Transposable-element insertions (Hi-C) | 2020 · Perl + R · bedtools | smoke num_candidate_insertions ≥ 1 | ✅ |
| **MaSIF-site** | Protein interaction sites | 2020 · Py3.6 · TF 1.12 · MSMS/APBS | **0.82 vs 0.85** (median ROC-AUC) | — |
| **ScanNet** | Protein binding sites | 2022 · Py3.6 · TF 1.14 · Keras | smoke ROC_AUC ≥ 0.7 | — |
| **Sequoya** | Multiple sequence alignment | 2020 · Py3.6 · jMetalPy | smoke sum_of_pairs_delta_vs_initial ≥ 0 | ✅ |

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

## CoCoNet  <small>`coconet_binning`</small>

Bin assembled viral contigs into genomes from composition + coverage with a deep siamese network.

- **Source:** [Puumanamana/CoCoNet](https://github.com/Puumanamana/CoCoNet) · Apache-2.0
- **Stack:** 2021 · Python · PyTorch
- **Sanity check:** `n_contigs_assigned ≥ 9`
- **Revived:** 30 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Arisdakessian et al., Bioinformatics 2021 — CoCoNet

```bash
lazarus pull coconet_binning
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-coconet:working` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## DeepLatentMicrobiome  <small>`deeplatentmicrobiome_env2otu`</small>

Predict a 717-OTU rhizosphere microbiome from 3 environmental features (age, temperature, precipitation) via a pretrained latent-space encoder/decoder.

- **Source:** [jorgemf/DeepLatentMicrobiome](https://github.com/jorgemf/DeepLatentMicrobiome) · Apache-2.0
- **Stack:** 2021 · Python · TF/Keras
- **Sanity check:** `pearson_r ≥ 0.65`  ·  **reproduced the paper:** mean per-sample Pearson r (n=373) **0.7368** vs 0.739
- **Revived:** 25 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Garcia-Jimenez et al., Bioinformatics 2021 — Deep latent space model for the rhizosphere microbiome

```bash
lazarus pull deeplatentmicrobiome_env2otu
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-dlm:working` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

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

## DnaFeaturesViewer  <small>`dnafeaturesviewer_genbank_plot`</small>

Render a GenBank record's annotated features as a linear feature map (PNG).

- **Source:** [Edinburgh-Genome-Foundry/DnaFeaturesViewer](https://github.com/Edinburgh-Genome-Foundry/DnaFeaturesViewer) · MIT
- **Stack:** Python · Biopython · matplotlib
- **Sanity check:** `feature_count ≥ 10`
- **Revived:** 15 autonomous agent-turns  ·  from a bare URL (Scout-planned)

```bash
lazarus pull dnafeaturesviewer_genbank_plot
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-dnafeaturesviewer:genbank-plot-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

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


## HiTEA  <small>`hitea`</small>

Call non-reference transposable-element (Alu/L1/SVA) insertions from a Hi-C BAM; emits a candidate-insertions BED + an HTML report.

- **Source:** [parklab/HiTea](https://github.com/parklab/HiTea) · MIT
- **Stack:** 2020 · Perl + R · bedtools
- **Sanity check:** `num_candidate_insertions ≥ 1`
- **Revived:** 14 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Chu, Nielsen et al., Nucleic Acids Research 2021 — HiTEA

```bash
lazarus pull hitea
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-hitea:working` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

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


## Sequoya  <small>`sequoya_nsgaii_msa`</small>

Multi-objective (NSGA-II) multiple sequence alignment optimizing sum-of-pairs and conserved columns.

- **Source:** [benhid/Sequoya](https://github.com/benhid/Sequoya) · MIT
- **Stack:** 2020 · Py3.6 · jMetalPy
- **Sanity check:** `sum_of_pairs_delta_vs_initial ≥ 0`
- **Revived:** 43 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Benítez-Hidalgo et al. — Sequoya: Multiobjective Multiple Sequence Alignment in Python

```bash
lazarus pull sequoya_nsgaii_msa
```

> ℹ️ The pinned image `ghcr.io/doctordean/lazarus-sequoya:nsgaii-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.
