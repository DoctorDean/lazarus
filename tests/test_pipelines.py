"""Tests for the composed-pipeline bricks under ``pipelines/``.

These adapters are the fusion logic of the ``target_dock_consensus`` flagship. Each one
ships twice: a readable ``.py`` (what these tests import) and a verbatim copy embedded in
the brick's ``lazarus.yaml`` entrypoint (so the contract is self-contained and needs no
build). ``test_adapter_source_matches_embedded_entrypoint`` is what keeps the two honest.

Offline — no Docker, no network, synthetic structures only.
"""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

PIPELINES = Path(__file__).resolve().parents[1] / "pipelines"
BRICKS = [("dock_prep", "prep.py"), ("dock_site_consensus", "consensus.py")]


def _load(brick: str, src: str):
    """Import an adapter that lives outside the package, by path."""
    spec = importlib.util.spec_from_file_location(f"_lz_{brick}", PIPELINES / brick / src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _embedded_python(brick: str) -> str:
    """The adapter source out of the brick's `python - <<'PY' ... PY` entrypoint."""
    entry = yaml.safe_load((PIPELINES / brick / "lazarus.yaml").read_text())["entrypoint"]
    return entry.split("<<'PY'\n", 1)[1].rsplit("\nPY\n", 1)[0]


# --------------------------------------------------------------------------
# contract / source parity
# --------------------------------------------------------------------------
@pytest.mark.parametrize("brick,src", BRICKS)
def test_adapter_source_matches_embedded_entrypoint(brick, src):
    """The .py and the copy embedded in the contract must not drift.

    Editing one without the other silently ships stale code in the brick, since the
    container runs the embedded copy while these tests exercise the file.
    """
    assert _embedded_python(brick).strip() == (PIPELINES / brick / src).read_text().strip(), (
        f"{brick}: {src} and the entrypoint in lazarus.yaml have diverged — "
        f"re-embed the file into the contract's `python - <<'PY'` heredoc."
    )


# --------------------------------------------------------------------------
# tiny structure builders
# --------------------------------------------------------------------------
def _pdb_line(rec, serial, name, resname, chain, resseq, x, y, z, elem):
    return (f"{rec:<6}{serial:>5} {name:^4} {resname:>3} {chain}{resseq:>4}    "
            f"{x:>8.3f}{y:>8.3f}{z:>8.3f}  1.00  0.00          {elem:>2}\n")


def _receptor(path, resids=(1, 2, 3, 4, 5)):
    """One CA + one CB per residue, strung out along x at 10 Å spacing."""
    with open(path, "w") as f:
        n = 0
        for rid in resids:
            for name, dx in (("CA", 0.0), ("CB", 1.5)):
                n += 1
                f.write(_pdb_line("ATOM", n, name, "ALA", "A", rid,
                                  10.0 * rid + dx, 0.0, 0.0, "C"))
        f.write("END\n")


def _sdf(path, coords, name="pose"):
    with open(path, "w") as f:
        f.write(f"{name}\n  lazarus\n\n")
        f.write(f"{len(coords):>3}{0:>3}  0  0  0  0  0  0  0  0999 V2000\n")
        for (x, y, z) in coords:
            f.write(f"{x:>10.4f}{y:>10.4f}{z:>10.4f} C   0  0  0  0  0  0  0  0  0  0  0  0\n")
        f.write("M  END\n$$$$\n")


def _het_pdb(path, coords, resname="JW4"):
    with open(path, "w") as f:
        for i, (x, y, z) in enumerate(coords, 1):
            f.write(_pdb_line("HETATM", i, "C1", resname, "A", 900, x, y, z, "C"))
        f.write("END\n")


# --------------------------------------------------------------------------
# dock_prep
# --------------------------------------------------------------------------
@pytest.fixture
def prep():
    return _load("dock_prep", "prep.py")


def _complex_pdb(path):
    """Protein + a 4-atom ligand + a 2-atom additive + water, as a crystal complex."""
    with open(path, "w") as f:
        f.write(_pdb_line("ATOM", 1, "CA", "ALA", "A", 1, 0.0, 0.0, 0.0, "C"))
        f.write(_pdb_line("ATOM", 2, "CA", "GLY", "A", 2, 3.8, 0.0, 0.0, "C"))
        for i in range(4):                                   # the real ligand (biggest group)
            f.write(_pdb_line("HETATM", 10 + i, "C1", "JW4", "A", 900, i, 1.0, 1.0, "C"))
        for i in range(2):                                   # a smaller non-solvent het group
            f.write(_pdb_line("HETATM", 20 + i, "C1", "ABC", "A", 901, i, 5.0, 5.0, "C"))
        f.write(_pdb_line("HETATM", 30, "O", "HOH", "A", 902, 9.0, 9.0, 9.0, "O"))
        f.write("END\n")


def test_dock_prep_splits_complex_and_writes_diffdock_csv(prep, tmp_path, monkeypatch):
    comp, smi, out = tmp_path / "c.pdb", tmp_path / "l.smi", tmp_path / "out"
    _complex_pdb(comp)
    smi.write_text("CCO ligand-name\n")                      # first token is the SMILES
    monkeypatch.setenv("OUTDIR", str(out))
    monkeypatch.setenv("complex", str(comp))
    monkeypatch.setenv("ligand_smiles", str(smi))
    prep.main()

    receptor = (out / "receptor.pdb").read_text()
    assert receptor.count("ATOM  ") == 2 and "HETATM" not in receptor

    # the largest non-solvent HETATM group is the reference ligand; water is never it
    ref = (out / "reference_ligand.pdb").read_text()
    assert ref.count("HETATM") == 4 and "JW4" in ref and "HOH" not in ref and "ABC" not in ref

    row = (out / "diffdock.csv").read_text().splitlines()[1]
    name, protein_path, smiles, _seq = row.split(",")
    assert name == "target"
    # must be the absolute in-container path where compose stages the `receptor` input
    assert protein_path == "/lazarus/in/receptor/receptor.pdb"
    assert smiles == "CCO"


def test_dock_prep_accepts_a_literal_smiles(prep, tmp_path, monkeypatch):
    """Standalone use passes the SMILES directly rather than as a file."""
    comp, out = tmp_path / "c.pdb", tmp_path / "out"
    _complex_pdb(comp)
    monkeypatch.setenv("OUTDIR", str(out))
    monkeypatch.setenv("complex", str(comp))
    monkeypatch.setenv("ligand_smiles", "c1ccccc1")
    prep.main()
    assert (out / "diffdock.csv").read_text().splitlines()[1].split(",")[2] == "c1ccccc1"


def test_dock_prep_handles_an_apo_structure(prep, tmp_path, monkeypatch):
    """No ligand at all: still emit the three files, with an empty reference."""
    comp, out = tmp_path / "apo.pdb", tmp_path / "out"
    comp.write_text(_pdb_line("ATOM", 1, "CA", "ALA", "A", 1, 0.0, 0.0, 0.0, "C") + "END\n")
    monkeypatch.setenv("OUTDIR", str(out))
    monkeypatch.setenv("complex", str(comp))
    monkeypatch.setenv("ligand_smiles", "CCO")
    prep.main()
    assert (out / "reference_ligand.pdb").read_text().strip() == "END"
    assert (out / "receptor.pdb").exists() and (out / "diffdock.csv").exists()


# --------------------------------------------------------------------------
# dock_site_consensus
# --------------------------------------------------------------------------
@pytest.fixture
def consensus():
    return _load("dock_site_consensus", "consensus.py")


def test_parsers_skip_hydrogens_and_other_chains(consensus, tmp_path):
    p = tmp_path / "r.pdb"
    with open(p, "w") as f:
        f.write(_pdb_line("ATOM", 1, "CA", "ALA", "A", 1, 0.0, 0.0, 0.0, "C"))
        f.write(_pdb_line("ATOM", 2, "HA", "ALA", "A", 1, 0.5, 0.0, 0.0, "H"))
        f.write(_pdb_line("ATOM", 3, "CA", "ALA", "B", 2, 5.0, 0.0, 0.0, "C"))
    res = consensus.parse_pdb_residues(p, chain="A")
    assert set(res) == {1} and len(res[1][1]) == 1          # hydrogen dropped, chain B dropped


def test_contact_and_distance_helpers(consensus, tmp_path):
    import numpy as np

    r = tmp_path / "r.pdb"
    _receptor(r, resids=(1, 2, 3))                           # CAs at x = 10, 20, 30
    residues = consensus.parse_pdb_residues(r)
    lig = np.array([[10.5, 0.0, 0.0]])                       # sits on residue 1 only
    assert consensus.contact_residues(lig, residues) == {1}
    assert consensus.contact_residues(np.empty((0, 3)), residues) == set()

    a = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    b = np.array([[1.0, 0.0, 0.0], [3.0, 0.0, 0.0]])
    assert consensus.rmsd_same_order(a, b) == pytest.approx(1.0)
    assert consensus.centroid_dist(a, b) == pytest.approx(1.0)
    # mismatched atom counts are not comparable in order — must not guess
    assert consensus.rmsd_same_order(a, b[:1]) is None
    assert consensus.centroid_dist(a, np.empty((0, 3))) is None


def test_load_pockets_sorts_by_druggability_and_tolerates_key_aliases(consensus, tmp_path):
    p = tmp_path / "pockets.json"
    p.write_text(json.dumps([
        {"rank": 1, "drug_score": 0.10, "lining_residues": [1, 2]},
        {"rank": 2, "druggability": 0.90, "residues": ["3", "4", "bogus"]},
    ]))
    pockets = consensus.load_pockets(p)
    assert [x["drug"] for x in pockets] == [0.90, 0.10]
    assert pockets[0]["residues"] == {3, 4}                  # unparseable resids dropped


def _consensus_inputs(tmp_path, *, druggability, scannet_p, pose_x=10.5):
    """A 5-residue receptor with both dockers landing on residues 1-3."""
    r = tmp_path / "receptor.pdb"
    _receptor(r)
    coords = [[pose_x, 0.0, 0.0], [pose_x + 10, 0.0, 0.0], [pose_x + 20, 0.0, 0.0]]
    _sdf(tmp_path / "dd.sdf", coords)
    _sdf(tmp_path / "eb.sdf", [[c[0] + 0.5, c[1], c[2]] for c in coords])
    _het_pdb(tmp_path / "ref.pdb", coords)                   # crystal pose == DiffDock's
    (tmp_path / "pockets.json").write_text(json.dumps(
        [{"rank": 1, "druggability": druggability, "lining_residues": [1, 2, 3]}]))
    with open(tmp_path / "scannet.csv", "w") as f:
        f.write("Chain,Residue Index,Binding site probability\n")
        for rid in range(1, 6):
            f.write(f"A,{rid},{scannet_p}\n")
    return {
        "OUTDIR": str(tmp_path / "out"),
        "receptor": str(r),
        "pockets": str(tmp_path / "pockets.json"),
        "scannet": str(tmp_path / "scannet.csv"),
        "diffdock_pose": str(tmp_path / "dd.sdf"),
        "equibind_pose": str(tmp_path / "eb.sdf"),
        "reference_ligand": str(tmp_path / "ref.pdb"),
    }


def test_consensus_confirms_a_small_molecule_site(consensus, tmp_path, monkeypatch, capsys):
    """Druggable pocket + both poses inside it + ScanNet quiet -> CONFIRMED (the BRD2 shape)."""
    env = _consensus_inputs(tmp_path, druggability=0.93, scannet_p=0.10)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    consensus.main()

    summary = (Path(env["OUTDIR"]) / "summary.txt").read_text()
    assert "CONFIRMED small-molecule site" in summary
    assert "stays quiet" in summary                          # not called a PPI interface
    assert "diffdock" in summary and "equibind" in summary

    metrics = dict(kv.split("=") for kv in capsys.readouterr().out.split())
    assert float(metrics["pocket_druggability"]) == pytest.approx(0.93)
    assert float(metrics["diffdock_pocket_overlap"]) == pytest.approx(1.0)
    assert float(metrics["equibind_pocket_overlap"]) == pytest.approx(1.0)
    # DiffDock's pose IS the reference here, so it must be exactly on top of it
    assert float(metrics["diffdock_centroid_to_ref_A"]) == pytest.approx(0.0, abs=1e-6)

    rows = (Path(env["OUTDIR"]) / "triage.csv").read_text().splitlines()
    assert rows[0].startswith("resid,resname,scannet_prob,in_top_pocket")
    assert len(rows) == 6                                    # header + 5 residues
    by_id = {r.split(",")[0]: r.split(",") for r in rows[1:]}
    assert by_id["1"][3] == "1" and by_id["1"][4] == "1"     # in pocket, contacted by DiffDock
    assert by_id["5"][3] == "0" and by_id["5"][4] == "0"     # untouched residue


def test_consensus_calls_a_flat_interface_a_biologic_target(consensus, tmp_path, monkeypatch):
    """No druggable pocket but ScanNet lit -> PPI verdict (the PD-L1 shape)."""
    env = _consensus_inputs(tmp_path, druggability=0.20, scannet_p=0.90)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    consensus.main()
    summary = (Path(env["OUTDIR"]) / "summary.txt").read_text()
    assert "PPI / biologic target" in summary
    assert "CONFIRMED" not in summary


def test_consensus_is_inconclusive_when_poses_miss_the_pocket(consensus, tmp_path, monkeypatch):
    env = _consensus_inputs(tmp_path, druggability=0.93, scannet_p=0.10, pose_x=200.0)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    consensus.main()
    assert "Inconclusive" in (Path(env["OUTDIR"]) / "summary.txt").read_text()


def test_consensus_runs_with_only_one_docker(consensus, tmp_path, monkeypatch):
    """A blocked brick must degrade to a partial verdict, not crash the pipeline."""
    env = _consensus_inputs(tmp_path, druggability=0.93, scannet_p=0.10)
    env["equibind_pose"] = str(tmp_path / "missing.sdf")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    consensus.main()
    summary = (Path(env["OUTDIR"]) / "summary.txt").read_text()
    assert "equibind: no pose (skipped / blocked)" in summary
    assert "CONFIRMED small-molecule site" in summary
