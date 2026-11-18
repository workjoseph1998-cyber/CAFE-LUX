# GitHub V4 review and cleanup inventory

Repository: `workjoseph1998-cyber/CAFE-LUX`. Inventory checked 2026-11-18. No remote branch/tag/release deletion, history rewrite, main merge or production deployment is part of the review push.

## Verified baseline and recovery

- Latest V3 source: `4aaa7fde15bcb41c1e0d90446fe53aa70aeae4af`.
- Remote main/V3 merge baseline: `de65594d21df274f1e7e29b6fd1e6184c772ebd7` (tree matches verified V3).
- Legacy remote default branch `feature/cafe-lux-v1`: `98d9f988de48c7d83cba76c7a7d94a06df260ab5` (V3 merge history).
- New review branch: `feature/cafe-lux-v4`, based on remote main; no force push.
- Retained recovery branch: `recovery/cafe-lux-v3` → `4aaa7fde15bcb41c1e0d90446fe53aa70aeae4af`; this is an archival recovery ref, not a maintained competing version. GitHub branch-protection configuration requires API/UI access and is not claimed here.
- Pre-change full Git backup: `/workspace/Cafe-LUX-before-v4.bundle`, verified with `git bundle verify`; SHA-256 `2902ae511e4d4e3c435642a6374b4995437a06459d50f43abf0156be32aee8e7`. It includes full existing history and local/remote references, including older histories. Preserve it separately from release ZIPs and production-data backups.

## Exact proposed remote branch deletions — AFTER approval and verified merge

| Remote ref | Recorded commit | Reason |
|---|---|---|
| `refs/heads/feature/cafe-lux-v1` | `98d9f988de48c7d83cba76c7a7d94a06df260ab5` | Legacy default/version alias, already merged into main |
| `refs/heads/feature/cafe-lux-v3-redesign` | `4aaa7fde15bcb41c1e0d90446fe53aa70aeae4af` | Completed V3 branch, retained separately by recovery ref |

`feature/cafe-lux-v4` may be removed only after its final reviewed commit is merged and tagged, with that exact commit recorded in the final approval inventory. Keep `main`, recovery ref, Git history and backups. No unrelated branches are included.

The current remote default is still `feature/cafe-lux-v1` according to `git ls-remote --symref origin HEAD`. Set **main** as GitHub's default before deleting the legacy default alias. This settings change cannot be performed through Git push.

## Tags and releases

Live `git ls-remote --tags origin` returned no tags at baseline. Stale local remote-tracking refs are not remote branches; only live refs listed above are deletion candidates.

The release API request `gh api repos/workjoseph1998-cyber/CAFE-LUX/releases` is blocked by this environment's network (`api.github.com`: Forbidden). Release entries/downloads therefore remain **unverified**. None are approved for deletion from an assumed inventory. Obtain an actual release/asset inventory with API/UI access, record IDs/tags/names/assets in a backup inventory, then request approval for those exact entries before deletion. No release deletion is claimed.

## Finalization after review

Review the V4 source/screenshots/test report and ZIP. Obtain approval to merge the reviewed V4 commit into main with history preserved; create final `v4.0.0` tag/release only after merge and verification. Rebuild and verify the ZIP/checksum for the final commit. Confirm the main/default/recovery refs, and only then perform the exact approved obsolete-branch cleanup. Publishing a final GitHub release and branch settings also need working API/UI access. No production deployment is implied by source approval.

The current tree replaces obsolete V3-only design/upgrade docs and screenshot sets with V4 documents/screenshots. Regression tests, legacy migration fixtures and historical changelog remain because they protect compatibility and recovery, not as active versions.
