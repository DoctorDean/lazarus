# Principled sample — design (the paper's headline numbers)

The pilot proved the instrument. This is the *unbiased* measurement — a **random**
draw from a defined frame, so the numbers survive a reviewer. Everything here is
pre-registered: inclusion rules, sanity criteria, tolerances, and caps are fixed
**before** we see results (most are already encoded in the harness).

## What we estimate (with 95% CIs)
1. **Decay rate** — fraction of published comp-bio methods that don't run today, agent-free.
2. **Revival rate** — fraction Lazarus revives (and separately, reproduces), of the dead ones and overall.
3. **Failure-mode distribution** — the reason-code taxonomy (itself a headline finding).

## The sampling frame (the crux)
Population = published comp-bio **methods/tools with a public code repo**, from a
defined venue set × year range. Draw a random sample; report on **all** of it.

- **Venue (decision):** journal-anchored on **_Bioinformatics_** (canonical, high
  volume, code-availability norms) — optionally widened to *PLOS Comp Biol / Nature
  Methods / NAR*. Alternatives: Papers-with-Code comp-bio tasks (ML-skewed), or the
  `bio.tools` registry. *Recommend Bioinformatics-anchored for a clean, defensible frame.*
- **Year range (decision):** **2018–2021** — old enough to have decayed, recent
  enough to be relevant and attemptable on one box.
- **Enumeration:** pull venue×year papers via the OpenAlex / Semantic Scholar API →
  keep those whose availability statement links a public GitHub/GitLab → population list.
- **Inclusion (pre-registered):** links a public repo; the repo is a *runnable method*
  (not a dataset- or analysis-only script); has a definable headline input→output for a
  sanity check; inference feasible on one x86 box (CPU or one ~20 GB GPU). **Every
  exclusion is logged with a reason** (needs a cluster, gated data, not a tool, …) — never
  silently dropped.
- **No overlap:** exclude the 6 originals and the 11 pilot repos — a *fresh* draw, so we
  don't measure our own tuning.

## Sample size
Precision × budget. N≈30 → ±~18 % (95 % Wilson); N≈50 → ±~14 %. Pilot cost was ~$1–9/repo.
**Recommend a first tranche of N = 30** (report CIs), expandable to 50. Random draw with a
**fixed seed** (reproducible).

## Protocol (per sampled repo)
1. **Baseline `naive_runs` (measures decay):** agent-free. In a clean container, follow the
   repo's README install and run its shipped example/quickstart, hard cap **K = 30 min**.
   `naive_runs = the example produced sane output`. Fair, fixed, documented. *(This runner
   still needs building — the one real new component.)*
2. **Lazarus attempt:** the hardened harness (Scout → resurrect → independent verify) under
   the fixed caps (90 turns · 90-min hard wall-clock · per-repo cost cap). Outcome + reason code.
3. Both run through the same `benchmark/run.py` + `results.json` machinery, resumable.

## Analysis
- Decay / revival / reproduction rates, each with a 95 % Wilson CI.
- Reason-code distribution (the failure taxonomy).
- Cost & turns per outcome; stratify by framework-era / domain if N allows.
- Headline framing: "*X %* of published comp-bio methods don't run today; Lazarus revives
  *Y %* of them (*Z %* reproducing the paper), autonomously, for ~$C each."

## Threats to validity (and mitigations)
- **Selection bias** → random draw + explicit frame + logged exclusions.
- **Overfitting** → fresh draw, zero overlap with originals/pilot.
- **Baseline fairness** → fixed, documented naive-run protocol.
- **Train-required repos** → a distinct outcome; note when training within budget is required.
- **Cost/time runaway** → hard container-level cap (watchdog) now enforced.

## Staging
1. **Build the frame** — scripted OpenAlex pull (venue×year) + GitHub-link filter → population.
2. **Draw** the seeded random sample; apply inclusion, logging exclusions.
3. **Build the baseline runner** (`naive_runs`) — the one new component.
4. **Run** baseline + Lazarus over the sample (budget-managed, resumable).
5. **Analyze + figures + write-up.**

## Open decisions for Dean
- **Frame:** Bioinformatics-anchored (rec) · multi-venue · Papers-with-Code.
- **Year range:** 2018–2021 (rec).
- **N:** 30 first tranche (rec) · 50.
- **Baseline judge:** how strictly to score "the example ran" (exact-output match vs "produced
  plausible output without erroring").
