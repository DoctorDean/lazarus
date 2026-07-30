# Registry

A living archive of tools Lazarus has brought back from the dead — each revived
from its source repo into a callable, containerised brick with a verified sanity
check, and (where a benchmark exists) a reproduced paper number.

**25 revived tools.** Pull any of them: `lazarus pull <name>`.

| Tool | Domain | Era / stack | Result | From a URL |
|---|---|---|---|:--:|
| **AHGestimation** | Hydrology | R | **0.997434 vs 0.9975** (continuity_exponent_sum) | ✅ |
| **AiZynthFinder** | Retrosynthesis | Py · ML | smoke is_solved ≥ 1 | ✅ |
| **Basset** | Genomics — chromatin accessibility | 2016 · Lua Torch7 | **0.894 vs 0.895** (mean AUROC (164 targets)) | ✅ |
| **CoCoNet** | Viral metagenome binning | 2021 · Python · PyTorch | smoke n_contigs_assigned ≥ 9 | ✅ |
| **DeepFRI** | Protein function prediction | Py · TensorFlow · protein LM | **0.99999 vs 0.99824** (top1_score_GO:0005509) | ✅ |
| **DeepLatentMicrobiome** | Microbiome — environment → OTUs | 2021 · Python · TF/Keras | **0.7368 vs 0.739** (mean per-sample Pearson r (n=373)) | ✅ |
| **DESPASITO** | Thermodynamics | Py · Numba | smoke aard_vapor_pressure < 0.15 | ✅ |
| **DiffDock** | Molecular docking | 2023 · PyTorch diffusion · ESM-2 · GPU | **0.375 vs 0.4** (top-1 success rate (<2Å)) | ✅ |
| **dMaSIF** | Protein interface (surface, GPU) | 2021 · Py3.6 · torch cu111 · PyKeOps · GPU | smoke ROCAUC ≥ 0.65 | — |
| **DnaFeaturesViewer** | Sequence annotation plots | Python · Biopython · matplotlib | smoke feature_count ≥ 10 | ✅ |
| **EquiBind** | Blind protein–ligand docking | 2022 · PyTorch · DGL · SE(3) | smoke ligand_centroid_distance_A < 10 | ✅ |
| **EquiDock** | Rigid protein–protein docking | 2022 · PyTorch · DGL · SE(3) | smoke ligand_CA_RMSD_vs_reference_output < 2 | ✅ |
| **fpocket** | Druggable pocket detection | 2010 C · built on modern GCC | smoke pockets ≥ 1 | — |
| **HiTEA** | Transposable-element insertions (Hi-C) | 2020 · Perl + R · bedtools | smoke num_candidate_insertions ≥ 1 | ✅ |
| **MaSIF-site** | Protein interaction sites | 2020 · Py3.6 · TF 1.12 · MSMS/APBS | **0.82 vs 0.85** (median ROC-AUC) | — |
| **matador** | Materials science / DFT | Py · materials informatics | smoke hull_dist_max_abs_error_vs_reference < 0.001 | ✅ |
| **MEIRLOP** | Genomics — motif enrichment | Py | **0.7814194753559087 vs 0.7814** (roc_auc) | ✅ |
| **PRODIGY-CRYSTAL** | Structural biology — interface classification | Py | smoke bio_probability ≥ 0.79 | ✅ |
| **PyAMG** | Numerical linear algebra | Py · C++ | smoke relative_residual < 1e-08 | ✅ |
| **ScanNet** | Protein binding sites | 2022 · Py3.6 · TF 1.14 · Keras | smoke ROC_AUC ≥ 0.7 | — |
| **Scikit-Topt** | Topology optimization | Py | smoke compliance_reduction_ratio ≥ 0.1 | ✅ |
| **Sequoya** | Multiple sequence alignment | 2020 · Py3.6 · jMetalPy | smoke sum_of_pairs_delta_vs_initial ≥ 0 | — |
| **SSALib** | Time-series analysis | Py | smoke reconstruction_relative_l2_error < 1e-06 | ✅ |
| **trRosetta** | Protein structure prediction | Py · TensorFlow | **1 vs 1** (pearson_r of flattened <8A contact maps) | ✅ |
| **W2W** | Urban climate / geospatial | Py · geospatial | smoke max_abs_diff_FRC_URB2D < 0.0001 | ✅ |

---

## AHGestimation  <small>`ahg_estimate`</small>

Robust, mass-conserving estimation of at-a-station hydraulic geometry from river channel measurements.

- **Source:** [mikejohnson51/AHGestimation](https://github.com/mikejohnson51/AHGestimation) · MIT
- **Stack:** R
- **Sanity check:** `continuity_exponent_sum_error < 0.05`  ·  **reproduced the paper:** continuity_exponent_sum **0.997434** vs 0.9975
- **Revived:** 17 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** AHGestimation: An R package for computing robust, mass preserving hydraulic geometries and rating curves (doi:10.21105/joss.06145)

```bash
lazarus pull ahg_estimate
```


## AiZynthFinder  <small>`aizynthfinder_retrosynthesis`</small>

Monte-Carlo tree search retrosynthetic route planning over reaction templates.

- **Source:** [MolecularAI/aizynthfinder](https://github.com/MolecularAI/aizynthfinder) · MIT
- **Stack:** Py · ML
- **Sanity check:** `is_solved ≥ 1`
- **Revived:** 21 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** AiZynthFinder: a fast, robust and flexible open-source software for retrosynthetic planning. (doi:10.1186/s13321-020-00472-1)

```bash
lazarus pull aizynthfinder_retrosynthesis
```


## Basset  <small>`basset_predict`</small>

Predict DNaseI-hypersensitivity across 164 cell types from a 600 bp DNA sequence.

- **Source:** [davek44/Basset](https://github.com/davek44/Basset) · MIT
- **Stack:** 2016 · Lua Torch7
- **Sanity check:** `min_perseq_std ≥ 0.01`  ·  **reproduced the paper:** mean AUROC (164 targets) **0.894** vs 0.895
- **Revived:** 48 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Kelley et al., Genome Research 2016 — Basset

```bash
lazarus pull basset_predict
```


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


## DeepFRI  <small>`deepfri_mf`</small>

Predict protein GO-term / EC function from structure via a graph convolutional network + protein language model.

- **Source:** [flatironinstitute/DeepFRI](https://github.com/flatironinstitute/DeepFRI) · BSD-3-Clause
- **Stack:** Py · TensorFlow · protein LM
- **Sanity check:** `top1_go_term_and_score ≥ 0.9`  ·  **reproduced the paper:** top1_score_GO:0005509 **0.99999** vs 0.99824
- **Revived:** 21 autonomous agent-turns  ·  from a bare URL (Scout-planned)

```bash
lazarus pull deepfri_mf
```


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


## DESPASITO  <small>`despasito_saft_gamma_mie_propane_saturation`</small>

SAFT-Gamma-Mie equation of state: parameterize and predict thermodynamic properties (e.g. vapor pressure).

- **Source:** [Santiso-Group/despasito](https://github.com/Santiso-Group/despasito) · BSD-3-Clause
- **Stack:** Py · Numba
- **Sanity check:** `aard_vapor_pressure < 0.15`
- **Revived:** 39 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** DESPASITO: A Python Package for SAFT EOS Parametrization and Thermodynamic Calculations (doi:10.21105/joss.07365)

```bash
lazarus pull despasito_saft_gamma_mie_propane_saturation
```


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


## EquiBind  <small>`equibind_blind_docking`</small>

Geometric deep learning for drug binding structure prediction — blind-dock a ligand into a protein in a single forward pass.

- **Source:** [HannesStark/EquiBind](https://github.com/HannesStark/EquiBind) · MIT
- **Stack:** 2022 · PyTorch · DGL · SE(3)
- **Sanity check:** `ligand_centroid_distance_A < 10`
- **Revived:** 32 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Stärk et al., ICML 2022 — EquiBind: Geometric Deep Learning for Drug Binding Structure Prediction

```bash
lazarus pull equibind_blind_docking
```


## EquiDock  <small>`equidock_rigid_docking`</small>

SE(3)-equivariant end-to-end rigid protein–protein docking — predict the docked complex in one shot, no candidate sampling.

- **Source:** [octavian-ganea/equidock_public](https://github.com/octavian-ganea/equidock_public) · MIT
- **Stack:** 2022 · PyTorch · DGL · SE(3)
- **Sanity check:** `ligand_CA_RMSD_vs_reference_output < 2`
- **Revived:** 44 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Ganea et al., ICLR 2022 — EquiDock: Independent SE(3)-Equivariant Models for End-to-End Rigid Protein Docking

```bash
lazarus pull equidock_rigid_docking
```


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


## matador  <small>`matador_kp_convex_hull`</small>

Aggregate, query and analyse first-principles (DFT) crystal-structure calculations; build phase-stability convex hulls.

- **Source:** [ml-evs/matador](https://github.com/ml-evs/matador) · MIT
- **Stack:** Py · materials informatics
- **Sanity check:** `hull_dist_max_abs_error_vs_reference < 0.001`
- **Revived:** 18 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** matador: a Python library for analysing, curating and performing high-throughput density-functional theory calculations (doi:10.21105/joss.02563)

```bash
lazarus pull matador_kp_convex_hull
```


## MEIRLOP  <small>`meirlop_motif_enrichment`</small>

Motif enrichment in ranked lists via logistic regression controlling for covariates.

- **Source:** [npdeloss/meirlop](https://github.com/npdeloss/meirlop) · MIT
- **Stack:** Py
- **Sanity check:** `roc_auc ≥ 0.75`  ·  **reproduced the paper:** roc_auc **0.7814194753559087** vs 0.7814
- **Revived:** 22 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** MEIRLOP: improving score-based motif enrichment by incorporating sequence bias covariates. (doi:10.1186/s12859-020-03739-4)

```bash
lazarus pull meirlop_motif_enrichment
```


## PRODIGY-CRYSTAL  <small>`prodigy_cryst`</small>

Classify a protein-protein interface as biological or crystallographic from interfacial contacts.

- **Source:** [haddocking/interface-classifier](https://github.com/haddocking/interface-classifier) · Apache-2.0
- **Stack:** Py
- **Sanity check:** `bio_probability ≥ 0.79`
- **Revived:** 10 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Distinguishing crystallographic from biological interfaces in protein complexes: role of intermolecular contacts and energetics for classification. (doi:10.1186/s12859-018-2414-9)

```bash
lazarus pull prodigy_cryst
```


## PyAMG  <small>`pyamg_ruge_stuben_solve`</small>

Algebraic multigrid solvers and preconditioners for large sparse linear systems.

- **Source:** [pyamg/pyamg](https://github.com/pyamg/pyamg) · MIT
- **Stack:** Py · C++
- **Sanity check:** `relative_residual < 1e-08`
- **Revived:** 11 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** PyAMG: Algebraic Multigrid Solvers in Python (doi:10.21105/joss.04142)

```bash
lazarus pull pyamg_ruge_stuben_solve
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


## Scikit-Topt  <small>`scikit_topt_oc`</small>

Structural topology optimization (optimality-criteria / MMA density methods) in Python.

- **Source:** [kevin-tofu/scikit-topt](https://github.com/kevin-tofu/scikit-topt) · Apache-2.0
- **Stack:** Py
- **Sanity check:** `compliance_reduction_ratio ≥ 0.1`
- **Revived:** 26 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** Scikit-Topt: A Python Library for Algorithm Development in Topology Optimization (doi:10.21105/joss.09092)

```bash
lazarus pull scikit_topt_oc
```


## Sequoya  <small>`sequoya_nsgaii_msa`</small>

Multi-objective (NSGA-II) multiple sequence alignment optimizing sum-of-pairs and conserved columns.

- **Source:** [benhid/Sequoya](https://github.com/benhid/Sequoya) · MIT
- **Stack:** 2020 · Py3.6 · jMetalPy
- **Sanity check:** `sum_of_pairs_delta_vs_initial ≥ 0`
- **Revived:** None autonomous agent-turns
- **Paper:** Benítez-Hidalgo et al. — Sequoya: Multiobjective Multiple Sequence Alignment in Python

```bash
lazarus pull sequoya_nsgaii_msa
```

> ℹ️ The pinned image `lazarus/sequoya:nsgaii-ready` isn't published yet — `pull` fetches the contract (API + CLI + Dockerfile + smoke test) so it can be rebuilt.

## SSALib  <small>`ssalib_sst_ssa`</small>

Singular Spectrum Analysis: decompose a time series into trend/oscillatory/noise components and reconstruct.

- **Source:** [ADSCIAN/ssalib](https://github.com/ADSCIAN/ssalib) · BSD-3-Clause
- **Stack:** Py
- **Sanity check:** `reconstruction_relative_l2_error < 1e-06`
- **Revived:** 24 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** SSALib: a Python Library for Time Series Decomposition using Singular Spectrum Analysis (doi:10.21105/joss.08600)

```bash
lazarus pull ssalib_sst_ssa
```


## trRosetta  <small>`trrosetta_predict`</small>

Predict inter-residue distance and orientation distributions from an MSA (feeds Rosetta folding).

- **Source:** [gjoni/trRosetta](https://github.com/gjoni/trRosetta) · MIT
- **Stack:** Py · TensorFlow
- **Sanity check:** `pearson_r ≥ 0.99`  ·  **reproduced the paper:** pearson_r of flattened <8A contact maps **1** vs 1
- **Revived:** 14 autonomous agent-turns  ·  from a bare URL (Scout-planned)

```bash
lazarus pull trrosetta_predict
```


## W2W  <small>`w2w_lcz_to_wrf`</small>

Inject WUDAPT Local Climate Zone maps into WRF geographic input for urban-canopy modelling.

- **Source:** [matthiasdemuzere/w2w](https://github.com/matthiasdemuzere/w2w) · MIT
- **Stack:** Py · geospatial
- **Sanity check:** `max_abs_diff_FRC_URB2D < 0.0001`
- **Revived:** 12 autonomous agent-turns  ·  from a bare URL (Scout-planned)
- **Paper:** W2W: A Python package that injects WUDAPT's Local Climate Zone information in WRF (doi:10.21105/joss.04432)

```bash
lazarus pull w2w_lcz_to_wrf
```

