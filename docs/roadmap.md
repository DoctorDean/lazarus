# Roadmap

Lazarus set out to prove one thing: that an agent can take dead research code — a bare
GitHub URL, nothing else — and bring it back as a callable, verified component. As of
**v0.5** that's proven, measured, and *used*:

- **It works, and it generalizes.** 40+ repositories revived across biology *and* a dozen
  other fields — from materials science and plasma physics to hydrology and retrosynthesis —
  at ~92% on both peer-reviewed and unreviewed code.
- **The problem is real and quantified.** A controlled study (peer-reviewed vs. unreviewed
  research software) shows unreviewed code is packaged half as often (42% vs. 95%) and fails
  to install today far more (61% vs. 37%) — yet is *just as recoverable*. The reviewed/unreviewed
  gap is **packaging discipline, not recoverability**.
- **The revivals are public.** A registry of 25 tools (23 pullable from GHCR), each with a
  verified contract, plus fixes sent upstream as pull requests.
- **And they compose into new science.** Four resurrected tools — spanning 2010→2023, C→Python,
  CPU→GPU — run as one pipeline and converge on a real drug pocket in BRD2, cross-validated
  sub-Å against the crystal ligand. Revival as a *supply chain*, not a museum.

That's the foundation. This document is where it goes next.

It's **tiered on purpose**. Tier 1 is the near-term direction — what we'd build next. Tier 2 is
what Lazarus *becomes* if it grows beyond a research project into standing infrastructure. Nothing
here is locked; it's an invitation. If one of these is what pulls you in, open an issue or a PR.

---

## Tier 1 — The next chapter

Two **durable** investments remain — the kind that compound. The flagship demonstration that used
to head this list is done; it's kept below as the worked example of what "finished" looks like.

### ✅ Shipped in v0.5 · Real science from resurrected bricks
*Was: build a genuine multi-tool pipeline entirely from tools that were dead a month ago, and
produce a real result.*

[`pipelines/target_dock_consensus.yaml`](https://github.com/DoctorDean/lazarus/blob/main/pipelines/target_dock_consensus.yaml)
runs fpocket (2010 C, geometry) + ScanNet (learned) + DiffDock (2023 generative, GPU) + EquiBind
(generative, CPU) as one `lazarus run` and triangulates a druggable site. On BRD2's BD2
bromodomain (PDB 6MOA): druggability **0.93**, ScanNet quiet at mean p **0.26**, both dockers
in-pocket at **0.20 Å** / **0.84 Å** from the crystal-ligand centroid, both converging on
**Asn429** and **Trp370** — the real BET pharmacophore. Verdict: *CONFIRMED small-molecule site* —
the mirror image of the PD-L1 pipeline's *flat interface, biologic target*. The full run is
committed at
[`pipelines/sample_output_6MOA/`](https://github.com/DoctorDean/lazarus/tree/main/pipelines/sample_output_6MOA),
including an honest note on which numbers reproduce exactly and which move (DiffDock is
generative). See [Compose & reproduce](compose.md).

### Durable · The reproducibility observatory
Turn the one-off benchmark into a *continuous* service: `decay-check` sweeping a large corpus (all
of JOSS, bioRxiv-linked repos), auto-reviving the dead ones, the registry growing to hundreds. A
public dashboard becomes a **live map of what science is rotting and what's been brought back**.

*Why it matters:* it makes the reproducibility crisis visible *and* actionable, every revival is a
public good, and it's an endless source of data for follow-on studies. *Good first steps:* schedule
`decay-check` over a seeded corpus; persist verdicts; a minimal dashboard over the results.

### Durable · A benchmark for reviving dead research code
The instrument already exists — seeded frames, an agent-free baseline, verified outcomes. Package it
as a public **leaderboard**: *SWE-bench for resurrecting dead scientific software.*

*Why it matters:* it recruits the whole AI-agent community to the problem, makes Lazarus the
reference implementation, and is a clean second paper. *Good first steps:* freeze a held-out repo
set + a scoring harness (install → run → verify); publish a submission format and a baseline.

---

## Tier 2 — If Lazarus becomes more than a research project

The tracks you invest in once one of the above builds momentum — turning a capability into a tool
people use, and a harder one.

### Adoption · Meet researchers where they are
Ship the dashboard ("search a repo, watch it revive live"), a **GitHub App / one-click "revive this
paper's code,"** and integrations (Zenodo, or JOSS running `decay-check` on submission). Turns a
capability into a daily tool — which brings users, feedback, hard real-world cases, and the
give-back loop at scale.

### The technical frontier · Harder revivals
Today's bar is *install + run + verify*. Push it to **full training reproduction** (not just
inference), **data- and credential-gated** tools, **multi-node / large-scale** jobs, and **new
languages** — there are mountains of dead scientific Fortran, MATLAB, and Julia nobody has touched.
Each one widens the set of science Lazarus can bring back.

---

## Get involved

- **Throw a dead repo at it.** The best test cases come from the wild — open an issue with a URL
  that won't run, or try `lazarus resurrect <url>` yourself.
- **Adopt a revival.** Browse the [registry](registry.md), `lazarus pull <name>`, and tell us where
  it breaks.
- **Pick up a direction above.** Any of these is a good first contribution — say hi in an issue and
  we'll help scope it.

*This roadmap is a living document; it will change as the work and the community do.*
