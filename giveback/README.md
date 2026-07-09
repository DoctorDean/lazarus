# Give back — contributing the revivals upstream

Lazarus doesn't just resurrect dead scientific code privately; it can **give the fixes
back to the community**. For each genuinely-abandoned repo it revived, we prepare a
maintainer-ready pull request: the real bug fix + a working path + a **CI smoke test** so
the method can't silently rot again.

## Which repos (and which we deliberately skip)

| Repo | Give back? | Why |
|---|---|---|
| **LPDI-EPFL/masif** | ✅ PR ready | Dead ~5 yrs, 50+ open issues; the rotted PDB download (#85) is a real, verified fix. |
| **jertubiana/ScanNet** | ✅ PR ready | `library_folder=''` breaks single-PDB inference (#15) — verified fix; #14 noted. |
| **FreyrS/dMaSIF** | ⛔ skip | License is **CC BY-NC-ND** (*no derivatives*) — we won't PR code changes to it. |
| **fpocket** (2010) | ⛔ skip | We revived the frozen 2010 SourceForge release; upstream (Discngine) is alive and already builds — nothing to fix. |

Picking the right targets — and *not* PRing a no-derivatives repo or a living one — is part
of doing this well.

## What's in each PR

- [`masif/`](masif/) — fixed `00-pdb_download.py` (direct RCSB fetch) + a CI smoke test
  that runs MaSIF-site on 4ZQK_A and asserts ROC-AUC ≥ 0.8. **Verified: 0.9137 via the
  built-in flow.**
- [`scannet/`](scannet/) — auto-detecting `library_folder` (`paths.py`) + a CI smoke test
  on 4ZQK_A `--noMSA`. **Verified: `prediction done!` from any working directory.**

Each folder has a `PR.md` (title + body) and the exact files to add. Both fixes were run
end-to-end on the real images before writing a single word of the PRs.
