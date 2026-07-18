"""Tests for the shipped decay-check — the pure pieces (no repo cloning / Docker)."""
import base64

from lazarus import decaycheck as dc


def test_readme_example_picks_usage_skips_install_and_trivial():
    md = ("# Tool\n## Install\n```bash\npip install tool\n```\n"
          "## Usage\n```python\nfrom tool import run\nrun('x')\n```\n")
    code = dc.readme_example(md)
    assert code and "run('x')" in code and "pip install" not in code
    # an R usage line survives next to a trivial library() line
    assert "simpg()" in dc.readme_example("```r\nlibrary(simurg)\npg <- simpg()\n```")
    # help/install/no-code blocks are not runnable examples
    assert dc.readme_example("```r\nhelp('simpg')\n```") is None
    assert dc.readme_example("```r\ninstall_github('a/b')\n```") is None
    assert dc.readme_example("no code blocks here") is None


def test_language_and_image():
    assert dc.primary_language({}) == "python"
    assert dc.primary_language({"R": 1000, "Python": 10}) == "r"
    assert dc.primary_language({"Python": 999, "C": 1}) == "python"
    assert "rocker" in dc.base_image_for("r")
    assert "miniconda" in dc.base_image_for("python")


def test_parse_verdict():
    out = "noise\nRAN: python x.py\n===DECAY=== naive_runs=1 stage=example reason=ran_ok\n"
    assert dc.parse_verdict(out) == (True, "example", "ran_ok")
    assert dc.parse_verdict("===DECAY=== naive_runs=0 stage=install reason=R_install_failed") \
        == (False, "install", "R_install_failed")
    assert dc.parse_verdict("no verdict here") is None


def test_build_script_substitutes_and_differs_by_sandbox():
    code = "from tool import run\nrun('x')"
    host = dc.build_script("https://github.com/o/r", sandbox="host", lang="python", readme_code=code)
    docker = dc.build_script("https://github.com/o/r", sandbox="docker", lang="python", readme_code=None)
    # placeholders are gone; the repo URL and verdict protocol are wired in
    for s in (host, docker):
        assert "REPO_URL" not in s and "PRIMARY_LANG" not in s
        assert "https://github.com/o/r" in s and "===DECAY===" in s
    # the README code is base64-injected (host run), absent when None (docker here)
    assert base64.b64encode(code.encode()).decode() in host
    assert "README_B64" not in host and "README_B64" not in docker
    # sandbox-specific isolation: host uses a venv/tmpdir, docker uses the container's /repo + conda
    assert "mktemp -d" in host and "python3 -m venv" in host
    assert "/repo" in docker and "conda env create" in docker


def test_decayresult_decayed_only_on_definite_false():
    assert dc.DecayResult("u", naive_runs=False).decayed is True
    assert dc.DecayResult("u", naive_runs=True).decayed is False
    assert dc.DecayResult("u", naive_runs=None).decayed is False   # inconclusive ≠ decayed
