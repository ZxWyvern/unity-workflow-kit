# 07 — Refresh Policy

Refresh is evidence invalidation + targeted revalidation, not a full rewrite.

## Refresh startup

1. Read current pack and current handoff.
2. Identify current repository snapshot/diff when available.
3. Determine which source/config/serialized/design/toolchain inputs changed.
4. Build the suspect-claim set using claim dependencies and invalidation triggers. Prefer the tool over doing it by hand:
   `python <pack_dir>/tools/suspects.py <repo_root> --pack <pack_dir> --since <recorded revision>`
   (or `--changed <paths...>` without git, plus `--trigger <token>` for toolchain, package, or design changes).
   The tool only reports suspect claims, findings to recheck, and checks to review; the agent edits the pack.
5. Always revalidate the handoff's next executable action before continuing it.

## Revalidation scope

Reverify:

- directly changed claim sources;
- claims depending on changed/invalidated claims;
- claims affected by Unity/package/build/design/entry-path/toolchain changes;
- execution results for changed behavior;
- stale handoff facts.

Leave unaffected sections untouched where possible.

## Runtime result carry-forward rule

Never carry an old execution result forward as proof of behavior that changed or whose relevant environment changed.

A check may remain documented, but its status must be reset to `not_run` when its previous observation no longer supports the current snapshot.

## Finding lifecycle

Findings have no status field. A finding is **closed** when its acceptance check is `passed` in the matrix and its evidence claims are not suspect. On the next Refresh, replace its detailed block with a one-line entry under a "Closed findings" heading in `project-context.md`: `- [F-005 | closed | V-003] short title`. The ID stays defined so references remain valid, and the validator requires the closing check to be `passed`. The validator warns when a closed finding is still listed as open.

## Workflow version

Bump `workflow_version` when generated workflow facts/routes/contracts materially change. Do not conflate this with the game/product version.

## Handoff replacement

`session-handoff.md` is current state, not an append-only history. Replace stale content each refresh/update. Version control already preserves history when available.
