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
        era="2016 · Lua Torch7", license="see source repo",
        # NOT published to GHCR pending an upstream license check (repo states none clearly).
        # Users rebuild locally via Lazarus; see docs/IMAGES.md.
        base_image="lazarus/basset:site-ready", gpu=False, from_url=True, turns=48,
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
        base_image="ghcr.io/doctordean/lazarus-dlm:working", gpu=False, from_url=True, turns=25,
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
        base_image="ghcr.io/doctordean/lazarus-hitea:working", gpu=False, from_url=True, turns=14,
        sanity_metric="num_candidate_insertions", sanity_threshold=1, sanity_direction="above",
        contract="examples/hitea_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="dnafeaturesviewer_genbank_plot", title="DnaFeaturesViewer",
        domain="Sequence annotation plots",
        summary="Render a GenBank record's annotated features as a linear feature map (PNG).",
        repo_url="https://github.com/Edinburgh-Genome-Foundry/DnaFeaturesViewer",
        paper="", era="Python · Biopython · matplotlib", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-dnafeaturesviewer:genbank-plot-ready", gpu=False, from_url=True, turns=15,
        sanity_metric="feature_count", sanity_threshold=10, sanity_direction="above",
        contract="examples/dnafeaturesviewer_genbank_plot_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="coconet_binning", title="CoCoNet", domain="Viral metagenome binning",
        summary="Bin assembled viral contigs into genomes from composition + coverage with a deep siamese network.",
        repo_url="https://github.com/Puumanamana/CoCoNet",
        paper="Arisdakessian et al., Bioinformatics 2021 — CoCoNet",
        era="2021 · Python · PyTorch", license="Apache-2.0",
        base_image="ghcr.io/doctordean/lazarus-coconet:working", gpu=False, from_url=True, turns=30,
        sanity_metric="n_contigs_assigned", sanity_threshold=9, sanity_direction="above",
        contract="examples/coconet_binning_contract", added="2026-07-18",
    ),
    RegistryEntry(
        name="sequoya_nsgaii_msa", title="Sequoya", domain="Multiple sequence alignment",
        summary="Multi-objective (NSGA-II) multiple sequence alignment optimizing sum-of-pairs and conserved columns.",
        repo_url="https://github.com/benhid/Sequoya",
        paper="Benítez-Hidalgo et al. — Sequoya: Multiobjective Multiple Sequence Alignment in Python",
        era="2020 · Py3.6 · jMetalPy", license="MIT",
        base_image="ghcr.io/doctordean/lazarus-sequoya:nsgaii-ready", gpu=False, from_url=True, turns=43,
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
        base_image="ghcr.io/doctordean/lazarus-equidock:working", gpu=False, from_url=True, turns=44,
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
        base_image="ghcr.io/doctordean/lazarus-equibind:contract-ready", gpu=False, from_url=True, turns=32,
        sanity_metric="ligand_centroid_distance_A", sanity_threshold=10, sanity_direction="below",
        contract="examples/equibind_blind_docking_contract", added="2026-07-18",
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
