#!/usr/bin/env python3
"""Seed + (re)generate the Lazarus registry.

Curated metadata for each revived tool lives here (the human bits the contract
doesn't carry: title, domain, era, one-line summary, license, agent-turns,
give-back PR). This writes:
  - registry/entries/<name>.yaml   (source of truth — the benchmark/bot append here)
  - registry/index.json            (aggregated, fetchable)
  - docs/registry.md               (the public index page)

Run from the repo root: python scripts/build_registry.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lazarus.registry import RegistryEntry, build_index, render_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

ENTRIES = [
    RegistryEntry(
        name="masif_site", title="MaSIF-site", domain="Protein interaction sites",
        summary="Predict per-residue protein-interaction-site probability from a molecular surface.",
        repo_url="https://github.com/LPDI-EPFL/masif",
        paper="Gainza et al., Nature Methods 2020 — MaSIF",
        era="2020 · Py3.6 · TF 1.12 · MSMS/APBS", license="Apache-2.0",
        base_image="ghcr.io/doctordean/lazarus-masif:site-ready", image_public=True, gpu=False, from_url=False, turns=18,
        sanity_metric="roc_auc", sanity_threshold=0.8, sanity_direction="above",
        reproduced_metric="median ROC-AUC", reproduced_reported=0.85, reproduced_measured=0.82,
        giveback_pr="https://github.com/LPDI-EPFL/masif/pull/93",
        contract="examples/masif_site_contract", added="2026-07-07",
    ),
    RegistryEntry(
        name="scannet_ppi_binding_sites", title="ScanNet", domain="Protein binding sites",
        summary="Per-residue protein–protein binding-site probability from one structure (structure-only, no MSA).",
        repo_url="https://github.com/jertubiana/ScanNet",
        paper="Tubiana et al., Nature Methods 2022 — ScanNet",
        era="2022 · Py3.6 · TF 1.14 · Keras", license="Apache-2.0",
        base_image="ghcr.io/doctordean/lazarus-scannet:ppi-noMSA-proven", image_public=True, gpu=False, from_url=False, turns=19,
        sanity_metric="ROC_AUC", sanity_threshold=0.7, sanity_direction="above",
        giveback_pr="https://github.com/jertubiana/ScanNet/pull/16",
        contract="examples/scannet_ppi_contract", added="2026-07-08",
    ),
    RegistryEntry(
        name="dmasif_site", title="dMaSIF", domain="Protein interface (surface, GPU)",
        summary="Differentiable molecular-surface interface prediction, built and run on GPU.",
        repo_url="https://github.com/FreyrS/dMaSIF",
        paper="Sverrisson et al., CVPR 2021 — dMaSIF",
        era="2021 · Py3.6 · torch cu111 · PyKeOps · GPU", license="CC BY-NC-ND",
        # NOT published to GHCR: CC BY-NC-ND forbids redistributing a derivative image.
        # Users rebuild locally via Lazarus; see docs/IMAGES.md.
        base_image="lazarus/dmasif:site-ready", gpu=True, from_url=False, turns=51,
        sanity_metric="ROCAUC", sanity_threshold=0.65, sanity_direction="above",
        contract="examples/dmasif_site_contract", added="2026-07-08",
    ),
    RegistryEntry(
        name="fpocket2", title="fpocket", domain="Druggable pocket detection",
        summary="Detect and rank druggable pockets on a protein structure (Voronoi / alpha-spheres).",
        repo_url="https://fpocket.sourceforge.net",
        paper="Le Guilloux et al., BMC Bioinformatics 2009 — fpocket",
        era="2010 C · built on modern GCC", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-fpocket:working", image_public=True, gpu=False, from_url=False, turns=32,
        sanity_metric="pockets", sanity_threshold=1, sanity_direction="above",
        contract="examples/fpocket2_contract", added="2026-07-08",
    ),
    RegistryEntry(
        name="basset_predict", title="Basset", domain="Genomics — chromatin accessibility",
        summary="Predict DNaseI-hypersensitivity across 164 cell types from a 600 bp DNA sequence.",
        repo_url="https://github.com/davek44/Basset",
        paper="Kelley et al., Genome Research 2016 — Basset",
        era="2016 · Lua Torch7", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-basset:site-ready", image_public=True, gpu=False, from_url=True, turns=48,
        sanity_metric="min_perseq_std", sanity_threshold=0.01, sanity_direction="above",
        reproduced_metric="mean AUROC (164 targets)", reproduced_reported=0.895, reproduced_measured=0.894,
        contract="examples/basset_predict_contract", added="2026-07-10",
    ),
    RegistryEntry(
        name="diffdock_blind_docking", title="DiffDock", domain="Molecular docking",
        summary="Blind docking — protein + ligand → ranked, confidence-scored 3D poses (diffusion model).",
        repo_url="https://github.com/gcorso/DiffDock",
        paper="Corso et al., ICLR 2023 — DiffDock",
        era="2023 · PyTorch diffusion · ESM-2 · GPU", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-diffdock:site-ready", image_public=True, gpu=True, from_url=True, turns=57,
        sanity_metric="rmsd", sanity_threshold=2.0, sanity_direction="below",
        reproduced_metric="top-1 success rate (<2Å)", reproduced_reported=0.40, reproduced_measured=0.375,
        contract="examples/diffdock_contract", added="2026-07-10",
    ),
    # --- promoted from the N=20 benchmark (permissive licenses only) ---
    # image_public stays False until scripts/publish_images.sh pushes each to GHCR.
    RegistryEntry(
        name="deeplatentmicrobiome_env2otu", title="DeepLatentMicrobiome",
        domain="Microbiome — environment → OTUs",
        summary="Predict a 717-OTU rhizosphere microbiome from 3 environmental features (age, temperature, precipitation) via a pretrained latent-space encoder/decoder.",
        repo_url="https://github.com/jorgemf/DeepLatentMicrobiome",
        paper="Garcia-Jimenez et al., Bioinformatics 2021 — Deep latent space model for the rhizosphere microbiome",
        era="2021 · Python · TF/Keras", license="Apache-2.0",
        base_image="ghcr.io/doctordean/lazarus-dlm:working", image_public=True, gpu=False, from_url=True, turns=25,
        sanity_metric="pearson_r", sanity_threshold=0.65, sanity_direction="above",
        reproduced_metric="mean per-sample Pearson r (n=373)", reproduced_reported=0.739, reproduced_measured=0.7368,
        contract="examples/deeplatentmicrobiome_env2otu_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="hitea", title="HiTEA", domain="Transposable-element insertions (Hi-C)",
        summary="Call non-reference transposable-element (Alu/L1/SVA) insertions from a Hi-C BAM; emits a candidate-insertions BED + an HTML report.",
        repo_url="https://github.com/parklab/HiTea",
        paper="Chu, Nielsen et al., Nucleic Acids Research 2021 — HiTEA",
        era="2020 · Perl + R · bedtools", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-hitea:working", image_public=True, gpu=False, from_url=True, turns=14,
        sanity_metric="num_candidate_insertions", sanity_threshold=1, sanity_direction="above",
        contract="examples/hitea_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="dnafeaturesviewer_genbank_plot", title="DnaFeaturesViewer",
        domain="Sequence annotation plots",
        summary="Render a GenBank record's annotated features as a linear feature map (PNG).",
        repo_url="https://github.com/Edinburgh-Genome-Foundry/DnaFeaturesViewer",
        paper="", era="Python · Biopython · matplotlib", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-dnafeaturesviewer:genbank-plot-ready", image_public=True, gpu=False, from_url=True, turns=15,
        sanity_metric="feature_count", sanity_threshold=10, sanity_direction="above",
        contract="examples/dnafeaturesviewer_genbank_plot_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="coconet_binning", title="CoCoNet", domain="Viral metagenome binning",
        summary="Bin assembled viral contigs into genomes from composition + coverage with a deep siamese network.",
        repo_url="https://github.com/Puumanamana/CoCoNet",
        paper="Arisdakessian et al., Bioinformatics 2021 — CoCoNet",
        era="2021 · Python · PyTorch", license="Apache-2.0",
        base_image="ghcr.io/doctordean/lazarus-coconet:working", image_public=True, gpu=False, from_url=True, turns=30,
        sanity_metric="n_contigs_assigned", sanity_threshold=9, sanity_direction="above",
        contract="examples/coconet_binning_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="sequoya_nsgaii_msa", title="Sequoya", domain="Multiple sequence alignment",
        summary="Multi-objective (NSGA-II) multiple sequence alignment optimizing sum-of-pairs and conserved columns.",
        repo_url="https://github.com/benhid/Sequoya",
        paper="Benítez-Hidalgo et al. — Sequoya: Multiobjective Multiple Sequence Alignment in Python",
        era="2020 · Py3.6 · jMetalPy", license="MIT",
        base_image="lazarus/sequoya:nsgaii-ready",  # held: 54.5GB image not published (rebuild-locally) gpu=False, from_url=True, turns=43,
        sanity_metric="sum_of_pairs_delta_vs_initial", sanity_threshold=0, sanity_direction="above",
        contract="examples/sequoya_nsgaii_msa_contract", added="2026-07-18",
    ),
    # --- SE(3)-equivariant docking, MIT (from the earlier comp-bio pilot) ---
    RegistryEntry(
        name="equidock_rigid_docking", title="EquiDock",
        domain="Rigid protein–protein docking",
        summary="SE(3)-equivariant end-to-end rigid protein–protein docking — predict the docked complex in one shot, no candidate sampling.",
        repo_url="https://github.com/octavian-ganea/equidock_public",
        paper="Ganea et al., ICLR 2022 — EquiDock: Independent SE(3)-Equivariant Models for End-to-End Rigid Protein Docking",
        era="2022 · PyTorch · DGL · SE(3)", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-equidock:working", image_public=True, gpu=False, from_url=True, turns=44,
        sanity_metric="ligand_CA_RMSD_vs_reference_output", sanity_threshold=2, sanity_direction="below",
        contract="examples/equidock_rigid_docking_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="equibind_blind_docking", title="EquiBind",
        domain="Blind protein–ligand docking",
        summary="Geometric deep learning for drug binding structure prediction — blind-dock a ligand into a protein in a single forward pass.",
        repo_url="https://github.com/HannesStark/EquiBind",
        paper="Stärk et al., ICML 2022 — EquiBind: Geometric Deep Learning for Drug Binding Structure Prediction",
        era="2022 · PyTorch · DGL · SE(3)", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-equibind:contract-ready", image_public=True, gpu=False, from_url=True, turns=32,
        sanity_metric="ligand_centroid_distance_A", sanity_threshold=10, sanity_direction="below",
        contract="examples/equibind_blind_docking_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name='deepfri_mf', title='DeepFRI', domain='Protein function prediction',
        summary='Predict protein GO-term / EC function from structure via a graph convolutional network + protein language model.',
        repo_url='https://github.com/flatironinstitute/DeepFRI',
        paper='', era='Py · TensorFlow · protein LM', license='BSD-3-Clause',
        base_image='ghcr.io/doctordean/lazarus-deepfri:working', image_public=True, gpu=False, from_url=True, turns=21,
        sanity_metric='top1_go_term_and_score', sanity_threshold=0.9, sanity_direction='above',
        reproduced_metric='top1_score_GO:0005509', reproduced_reported=0.99824, reproduced_measured=0.99999,
        contract='examples/deepfri_mf_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='trrosetta_predict', title='trRosetta', domain='Protein structure prediction',
        summary='Predict inter-residue distance and orientation distributions from an MSA (feeds Rosetta folding).',
        repo_url='https://github.com/gjoni/trRosetta',
        paper='', era='Py · TensorFlow', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-trrosetta:predict-ready', image_public=True, gpu=False, from_url=True, turns=14,
        sanity_metric='pearson_r', sanity_threshold=0.99, sanity_direction='above',
        reproduced_metric='pearson_r of flattened <8A contact maps', reproduced_reported=1, reproduced_measured=1,
        contract='examples/trrosetta_predict_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='matador_kp_convex_hull', title='matador', domain='Materials science / DFT',
        summary='Aggregate, query and analyse first-principles (DFT) crystal-structure calculations; build phase-stability convex hulls.',
        repo_url='https://github.com/ml-evs/matador',
        paper='matador: a Python library for analysing, curating and performing high-throughput density-functional theory calculations (doi:10.21105/joss.02563)', era='Py · materials informatics', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-matador:hull-ready', image_public=True, gpu=False, from_url=True, turns=18,
        sanity_metric='hull_dist_max_abs_error_vs_reference', sanity_threshold=0.001, sanity_direction='below',
        contract='examples/matador_kp_convex_hull_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='ahg_estimate', title='AHGestimation', domain='Hydrology',
        summary='Robust, mass-conserving estimation of at-a-station hydraulic geometry from river channel measurements.',
        repo_url='https://github.com/mikejohnson51/AHGestimation',
        paper='AHGestimation: An R package for computing robust, mass preserving hydraulic geometries and rating curves (doi:10.21105/joss.06145)', era='R', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-ahgestimation:ready', image_public=True, gpu=False, from_url=True, turns=17,
        sanity_metric='continuity_exponent_sum_error', sanity_threshold=0.05, sanity_direction='below',
        reproduced_metric='continuity_exponent_sum', reproduced_reported=0.9975, reproduced_measured=0.997434,
        contract='examples/ahg_estimate_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='scikit_topt_oc', title='Scikit-Topt', domain='Topology optimization',
        summary='Structural topology optimization (optimality-criteria / MMA density methods) in Python.',
        repo_url='https://github.com/kevin-tofu/scikit-topt',
        paper='Scikit-Topt: A Python Library for Algorithm Development in Topology Optimization (doi:10.21105/joss.09092)', era='Py', license='Apache-2.0',
        base_image='ghcr.io/doctordean/lazarus-scikit-topt:oc-working', image_public=True, gpu=False, from_url=True, turns=26,
        sanity_metric='compliance_reduction_ratio', sanity_threshold=0.1, sanity_direction='above',
        contract='examples/scikit_topt_oc_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='ssalib_sst_ssa', title='SSALib', domain='Time-series analysis',
        summary='Singular Spectrum Analysis: decompose a time series into trend/oscillatory/noise components and reconstruct.',
        repo_url='https://github.com/ADSCIAN/ssalib',
        paper='SSALib: a Python Library for Time Series Decomposition using Singular Spectrum Analysis (doi:10.21105/joss.08600)', era='Py', license='BSD-3-Clause',
        base_image='ghcr.io/doctordean/lazarus-ssalib:ssa-ready', image_public=True, gpu=False, from_url=True, turns=24,
        sanity_metric='reconstruction_relative_l2_error', sanity_threshold=1e-06, sanity_direction='below',
        contract='examples/ssalib_sst_ssa_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='despasito_saft_gamma_mie_propane_saturation', title='DESPASITO', domain='Thermodynamics',
        summary='SAFT-Gamma-Mie equation of state: parameterize and predict thermodynamic properties (e.g. vapor pressure).',
        repo_url='https://github.com/Santiso-Group/despasito',
        paper='DESPASITO: A Python Package for SAFT EOS Parametrization and Thermodynamic Calculations (doi:10.21105/joss.07365)', era='Py · Numba', license='BSD-3-Clause',
        base_image='ghcr.io/doctordean/lazarus-despasito:propane-sat-working', image_public=True, gpu=False, from_url=True, turns=39,
        sanity_metric='aard_vapor_pressure', sanity_threshold=0.15, sanity_direction='below',
        contract='examples/despasito_saft_gamma_mie_propane_saturation_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='pyamg_ruge_stuben_solve', title='PyAMG', domain='Numerical linear algebra',
        summary='Algebraic multigrid solvers and preconditioners for large sparse linear systems.',
        repo_url='https://github.com/pyamg/pyamg',
        paper='PyAMG: Algebraic Multigrid Solvers in Python (doi:10.21105/joss.04142)', era='Py · C++', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-pyamg:solve-ready', image_public=True, gpu=False, from_url=True, turns=11,
        sanity_metric='relative_residual', sanity_threshold=1e-08, sanity_direction='below',
        contract='examples/pyamg_ruge_stuben_solve_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='w2w_lcz_to_wrf', title='W2W', domain='Urban climate / geospatial',
        summary='Inject WUDAPT Local Climate Zone maps into WRF geographic input for urban-canopy modelling.',
        repo_url='https://github.com/matthiasdemuzere/w2w',
        paper="W2W: A Python package that injects WUDAPT's Local Climate Zone information in WRF (doi:10.21105/joss.04432)", era='Py · geospatial', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-w2w:working', image_public=True, gpu=False, from_url=True, turns=12,
        sanity_metric='max_abs_diff_FRC_URB2D', sanity_threshold=0.0001, sanity_direction='below',
        contract='examples/w2w_lcz_to_wrf_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='aizynthfinder_retrosynthesis', title='AiZynthFinder', domain='Retrosynthesis',
        summary='Monte-Carlo tree search retrosynthetic route planning over reaction templates.',
        repo_url='https://github.com/MolecularAI/aizynthfinder',
        paper='AiZynthFinder: a fast, robust and flexible open-source software for retrosynthetic planning. (doi:10.1186/s13321-020-00472-1)', era='Py · ML', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-aizynth:working', image_public=True, gpu=False, from_url=True, turns=21,
        sanity_metric='is_solved', sanity_threshold=1, sanity_direction='above',
        contract='examples/aizynthfinder_retrosynthesis_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='meirlop_motif_enrichment', title='MEIRLOP', domain='Genomics — motif enrichment',
        summary='Motif enrichment in ranked lists via logistic regression controlling for covariates.',
        repo_url='https://github.com/npdeloss/meirlop',
        paper='MEIRLOP: improving score-based motif enrichment by incorporating sequence bias covariates. (doi:10.1186/s12859-020-03739-4)', era='Py', license='MIT',
        base_image='ghcr.io/doctordean/lazarus-meirlop:working', image_public=True, gpu=False, from_url=True, turns=22,
        sanity_metric='roc_auc', sanity_threshold=0.75, sanity_direction='above',
        reproduced_metric='roc_auc', reproduced_reported=0.7814, reproduced_measured=0.7814194753559087,
        contract='examples/meirlop_motif_enrichment_contract', added="2026-07-28",
    ),
    RegistryEntry(
        name='prodigy_cryst', title='PRODIGY-CRYSTAL', domain='Structural biology — interface classification',
        summary='Classify a protein-protein interface as biological or crystallographic from interfacial contacts.',
        repo_url='https://github.com/haddocking/interface-classifier',
        paper='Distinguishing crystallographic from biological interfaces in protein complexes: role of intermolecular contacts and energetics for classification. (doi:10.1186/s12859-018-2414-9)', era='Py', license='Apache-2.0',
        base_image='ghcr.io/doctordean/lazarus-prodigy-cryst:bio-ready', image_public=True, gpu=False, from_url=True, turns=10,
        sanity_metric='bio_probability', sanity_threshold=0.79, sanity_direction='above',
        contract='examples/prodigy_cryst_contract', added="2026-07-28",
    ),
]


def main() -> None:
    entries = sorted(ENTRIES, key=lambda e: e.title.lower())
    edir = ROOT / "registry" / "entries"
    edir.mkdir(parents=True, exist_ok=True)
    for e in entries:
        (edir / f"{e.name}.yaml").write_text(e.to_yaml(), encoding="utf-8")
    (ROOT / "registry" / "index.json").write_text(
        json.dumps(build_index(entries), indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "docs" / "registry.md").write_text(render_markdown(entries), encoding="utf-8")
    print(f"wrote {len(entries)} entries + index.json + docs/registry.md")


if __name__ == "__main__":
    main()
