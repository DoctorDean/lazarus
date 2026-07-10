# Compose & reproduce

## Compose — a pipeline from revived bricks

Because every revival speaks the same contract, revived tools compose regardless of domain,
language, or era. A pipeline is a small YAML; one command runs it, passing file artifacts between
steps on the host you choose.

[`examples/pipelines/binder_triage.yaml`](https://github.com/DoctorDean/lazarus/blob/main/examples/pipelines/binder_triage.yaml)
assembles three methods that were each individually unrunnable a week ago:

```
structure ─▶ ScanNet ─┐
          ─▶ dMaSIF ──┼─▶ consensus ─▶ interface residues that also line a druggable pocket
          ─▶ fpocket ─┘
```

```bash
lazarus run examples/pipelines/binder_triage.yaml \
  --input structure=4ZQK.pdb \
  --registry examples --registry components \
  --docker-host ssh://you@your-x86-gpu-box
```

Run live on **PD-L1**, it concluded: **27 interface residues** clearly localized, but **0 druggable
pockets** among them → *"a flat protein-protein interface: an antibody / biologic target, not a
small-molecule one."* That's textbook immuno-oncology (PD-1/PD-L1 *is* an antibody target),
reproduced from dead code.

## Reproduce — the trust layer

A smoke test proves a method *runs*; a benchmark proves it's *the method*. A contract's `benchmark`
field emits a `REPRODUCE.md` certificate with a PASS/OFF verdict.

| Method | Paper | Lazarus | Verdict |
|---|:--:|:--:|:--:|
| **MaSIF-site** transient PPI benchmark | 0.85 | 0.82 | reproduced (±0.05) |
| **Basset** mean AUROC over 164 cell types | 0.895 | 0.8944 | reproduced |

Basset's reproduction is what *exposed* a silent bug: the naive run scored mean AUROC 0.675 because
half the genome's soft-masked (lowercase) bases fell through the one-hot encoder. Reproducing the
paper — not merely executing the code — is what caught it. Full story:
[the hard problems it solved](CHALLENGES.md).

## Give back

For the genuinely-abandoned repos, Lazarus prepares maintainer-ready PRs — the real fix plus a CI
smoke test so the method can't silently rot again:

- **MaSIF** — [PR #93](https://github.com/LPDI-EPFL/masif/pull/93): the rotted PDB download, fixed.
- **ScanNet** — [PR #16](https://github.com/jertubiana/ScanNet/pull/16): `library_folder=''` auto-detects the repo root.
