# 07 — Refresh Policy

Refresh is evidence invalidation + targeted revalidation, not a full rewrite.

## Refresh startup

1. Read applicable instructions, `agent.md`, the index snapshot, and the active `sessions/<branch-slug>__<actor-slug>.md`. Use the tools to select affected blocks instead of loading the entire pack.
2. Identify current repository snapshot/diff when available.
3. Determine which source/config/serialized/design/toolchain inputs changed.
4. Build the suspect-claim set using claim dependencies and invalidation triggers. Prefer the tool over doing it by hand:
   `python <pack_dir>/tools/suspects.py <repo_root> --pack <pack_dir> --since <recorded revision>`
   (or `--changed <paths...>` without git, plus `--trigger <token>` for toolchain, package, or design changes).
   The tool also scans files that mention C# types declared in changed files, so likely call sites become suspects without a repository-wide search. The tool only reports suspect claims, findings to recheck, and checks to review; the agent edits the pack.
5. Always revalidate the active session's next executable action before continuing it.
6. After structural document changes, regenerate `index.json` with `python <pack_dir>/tools/packlib.py index <repo_root> --pack <pack_dir>`. The file is generated; do not hand-edit it.

`--since` includes tracked changes and untracked, nonignored files. It compares against a commit, not the exact earlier dirty working tree. If the recorded snapshot was dirty, revision is unavailable, export completeness changed, or external toolchain state changed, inspect the recorded limits and broaden revalidation explicitly. Never interpret an empty Git diff as proof that a dirty snapshot is unchanged. Fire environment/package/design triggers explicitly; filename comparison alone cannot discover them.

If nothing relevant changed and the next action is still valid, leave the pack unchanged. Do not rewrite dates, bump versions, or regenerate identical prose just to report a refresh. In routine implementation sessions, update only affected claims/checks and the handoff; the generator kit does not need to be reloaded.

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

## Session replacement

Each `sessions/<branch-slug>__<actor-slug>.md` is current state for that branch and actor, not an append-only history. Replace stale content in your own file each refresh/update; leave other actors' files alone. Version control already preserves history when available. Legacy `session-handoff.md` is accepted with a warning and should be migrated.
