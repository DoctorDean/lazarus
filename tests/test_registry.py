"""Tests for the registry data layer: entries, catalog loading, index, pull."""
from pathlib import Path

import pytest

from lazarus import registry as reg

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry"


def test_local_catalog_loads_all_entries():
    catalog = reg.load_catalog(str(REG))
    names = {e.name for e in catalog}
    assert {"masif_site", "diffdock_blind_docking", "basset_predict"} <= names
    assert len(catalog) >= 6
    # sorted by title
    titles = [e.title.lower() for e in catalog]
    assert titles == sorted(titles)


def test_get_by_name_and_title():
    catalog = reg.load_catalog(str(REG))
    assert reg.get(catalog, "diffdock_blind_docking").title == "DiffDock"
    assert reg.get(catalog, "DiffDock").name == "diffdock_blind_docking"
    with pytest.raises(KeyError):
        reg.get(catalog, "nope")


def test_entry_derived_fields():
    catalog = reg.load_catalog(str(REG))
    dd = reg.get(catalog, "diffdock_blind_docking")
    assert dd.sanity_direction == "below"
    assert dd.sanity_str() == "rmsd < 2.0"      # lower-is-better renders with '<'
    assert dd.reproduced is True
    assert "reproduced" in dd.headline()

    scannet = reg.get(catalog, "scannet_ppi_binding_sites")
    assert scannet.reproduced is False
    assert scannet.sanity_str() == "ROC_AUC ≥ 0.7"
    assert scannet.headline().startswith("revived")


def test_roundtrip_dict():
    e = reg.RegistryEntry(name="x", title="X", domain="d", summary="s",
                          repo_url="u", paper="p", era="e", license="MIT",
                          base_image="img", sanity_metric="m", sanity_threshold=1.0)
    assert reg.RegistryEntry.from_dict(e.to_dict()) == e


def test_index_and_markdown_render():
    catalog = reg.load_catalog(str(REG))
    idx = reg.build_index(catalog)
    assert idx["count"] == len(catalog) and idx["schema"] == 1
    md = reg.render_markdown(catalog)
    assert "# Registry" in md and "DiffDock" in md and "lazarus pull" in md


def test_pull_from_local_registry(tmp_path):
    out = reg.pull("diffdock_blind_docking", dest=str(tmp_path), source=str(REG))
    assert (out / "lazarus.yaml").exists()
    assert (out / "predict.py").exists()
