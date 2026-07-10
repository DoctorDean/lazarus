# Publishing `lazarus-bio` to PyPI

Publishing is automated via **PyPI Trusted Publishing** (OIDC) — no API tokens are
stored in the repo or in GitHub secrets. You cut a GitHub Release; the
[`publish`](https://github.com/DoctorDean/lazarus/blob/main/.github/workflows/publish.yml) workflow builds and uploads.

## One-time setup

1. **Reserve the Trusted Publisher on PyPI** (works before the project exists, as a
   "pending publisher"):
   - Log in to <https://pypi.org> → *Your projects* → *Publishing* → *Add a pending publisher*.
   - PyPI Project Name: `lazarus-bio`
   - Owner: `DoctorDean` · Repository: `lazarus`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
2. **Create the GitHub environment** `pypi`: repo *Settings → Environments → New environment → `pypi`*.

## Cut a release

```bash
# bump the version in pyproject.toml (e.g. 0.1.0 -> 0.1.1), commit, then:
git tag v0.1.0
git push origin v0.1.0
```

Then on GitHub: *Releases → Draft a new release → choose tag `v0.1.0` → Publish*.
The `publish` workflow runs, builds the sdist + wheel, and uploads to PyPI. Within a
minute `pip install lazarus-bio` serves the new version.

> The tag is cosmetic; PyPI takes the version from `pyproject.toml`. Keep them in sync
> — `lazarus.__version__` reads the installed metadata, so there is nothing else to bump.

## Manual fallback (local build + upload)

If you'd rather publish by hand once (e.g. to claim the name), build and upload with a
[PyPI API token](https://pypi.org/manage/account/token/):

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*        # username: __token__ · password: your pypi-... token
```

Both paths produce the same artifacts; `twine check` already passes locally.
