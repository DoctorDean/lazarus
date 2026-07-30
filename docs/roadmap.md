# Roadmap

Lazarus set out to prove one thing: that an agent can take dead research code — a bare
GitHub URL, nothing else — and bring it back as a callable, verified component. As of
**v0.4** that's proven and measured:

- **It works, and it generalizes.** 40+ repositories revived across biology *and* a dozen
  other fields — from materials science and plasma physics to hydrology and retrosynthesis —
  at ~92% on both peer-reviewed and unreviewed code.
- **The problem is real and quantified.** A controlled study (peer-reviewed vs. unreviewed
  research software) shows unreviewed code is packaged half as often (42% vs. 95%) and fails
  to install today far more (61% vs. 37%) — yet is *just as recoverable*. The reviewed/unreviewed
  gap is **packaging discipline, not recoverability**.
- **The revivals are public.** A registry of 25 tools (23 pullable from GHCR), each with a
  verified contract, plus fixes sent upstream as pull requests.

That's the foundation. This document is where it goes next.

It's **tiered on purpose**. Tier 1 is the near-term direction — what we'd build next. Tier 2 is
what Lazarus *becomes* if it grows beyond a research project into standing infrastructure. Nothing
here is locked; it's an invitation. If one of these is what pulls you in, open an issue or a PR.

---

## Tier 1 — The next chapter

Three directions, best pursued as a pair: one **flagship** demonstration for reach, and one
**durable** investment that compounds.

### Flagship · Real science from resurrected bricks
The `compose`/contract layer already lets revived tools snap together — but the vision (revival as
a *supply chain for new work*, not a museum) is under-demonstrated. Build a genuine multi-tool
pipeline entirely from tools that were dead a month ago — e.g. structural biology:
pocket detection (`fpocket`) → docking (`DiffDock` / `EquiBind`) → interface classification
(`PRODIGY-CRYSTAL`) → scoring — and produce a **real result**.

*Why it matters:* it's the most quotable proof there is, and it lands hardest with the scientists
who feel the reproducibility pain. *Good first steps:* pick a question answerable by 3–4 registry
bricks; wire the contracts into one `compose` pipeline; write up the result and the fact that every
component was unrunnable a week prior.

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
