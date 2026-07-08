"""Tests for the integration contract schema and emitter."""

from pathlib import Path

from lazarus.contract import (
    Contract,
    IOSpec,
    SmokeCheck,
    emit,
    render_dockerfile,
    render_predict_py,
    render_smoke_test,
)


def masif_site_contract() -> Contract:
    """The concrete target for the MaSIF resurrection -- doubles as a spec."""
    return Contract(
        name="masif_site",
        repo_url="https://github.com/LPDI-EPFL/masif",
        base_image="lazarus/masif:site-ready",
        entrypoint=(
            "cd /masif/data/masif_site && "
            "./data_prepare_one.sh --file $INPUT XXXX_A && "
            "./predict_site.sh XXXX_A && "
            "cp -r output/all_feat_3l/pred_data/* $OUTDIR/"
        ),
        inputs=[IOSpec("structure", "path:pdb", "a single-chain PDB file")],
        outputs=[IOSpec("scores", "path:npy", "per-vertex interaction-site scores")],
        smoke=SmokeCheck(
            description="known interface on 4ZQK_A scores high",
            command="cd /masif/data/masif_site && ./color_site.sh 4ZQK_A | tail -1",
            metric="roc_auc",
            threshold=0.8,
            input_ref="4ZQK_A",
        ),
        paper="Gainza et al., Nat. Methods 2020",
        commit="master",
        patches=["bypass rotted RCSB download via data_prepare_one.sh --file (issue #85)"],
    )


def test_yaml_roundtrip_preserves_everything():
    c = masif_site_contract()
    back = Contract.from_yaml(c.to_yaml())
    assert back == c
    assert back.smoke.metric == "roc_auc"
    assert back.inputs[0].type == "path:pdb"


def test_dockerfile_names_image_and_patches():
    text = render_dockerfile(masif_site_contract())
    assert "FROM lazarus/masif:site-ready" in text
    assert "issue #85" in text


def test_predict_py_is_valid_python_and_carries_entrypoint():
    text = render_predict_py(masif_site_contract())
    compile(text, "predict.py", "exec")   # must be syntactically valid
    assert "predict_site.sh" in text
    assert 'IMAGE = "lazarus/masif:site-ready"' in text


def test_smoke_test_is_valid_python_and_encodes_threshold():
    text = render_smoke_test(masif_site_contract())
    compile(text, "smoke_test.py", "exec")
    assert "roc_auc" in text
    assert "THRESHOLD = 0.8" in text


def test_emitter_escapes_quotes_and_newlines():
    # Regression: the real agent-emitted smoke command contained
    # awk '{print "roc_auc="$1}' — embedded double-quotes that broke the
    # naive "..." template. Entrypoints are multi-line too.
    c = Contract(
        name="q",
        repo_url="",
        base_image="img:x",
        entrypoint='echo "hi $INPUT"\ncd /x && run --flag "a b" > "$OUTDIR/o"\n',
        smoke=SmokeCheck(
            description='first line\nsecond with "quotes"',
            command="run 2>&1 | awk '{print \"roc_auc=\"$1}'",
            metric="roc_auc",
            threshold=0.8,
        ),
    )
    compile(render_predict_py(c), "predict.py", "exec")   # must stay valid Python
    compile(render_smoke_test(c), "smoke_test.py", "exec")


def test_emit_writes_full_package(tmp_path):
    out = emit(masif_site_contract(), tmp_path / "pkg")
    written = {p.name for p in Path(out).iterdir()}
    assert written == {"lazarus.yaml", "Dockerfile", "predict.py", "smoke_test.py"}
    # the serialized contract should round-trip from the emitted file
    reloaded = Contract.from_yaml((out / "lazarus.yaml").read_text())
    assert reloaded.name == "masif_site"
