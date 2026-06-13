# ADR 0014: Purge superseded draft material from git history before public release

## Status
Proposed (pre-registered before the rewrite; ADR-before-fix discipline).
Destructive history operation — requires explicit go before execution.

## Context

Repo `avalyset/chatcat` is private, `origin/main = 32b1829`, working tree
clean. The decision to take the repo public is decoupled from the arXiv
preprint and is now gated on this operation, not on a calendar date.

A read-only history investigation (2026-06-13) established:

- HEAD (`32b1829`) is clean: `git grep` for all four scrub terms returns
  nothing. The committed arXiv bundle (`paper/arxiv/...tar.gz`) was built
  from clean HEAD and does not contain the material.
- Earlier draft material — a discussion subsection plus supporting
  sentences, reserved for separate future work — survives in three
  pre-scrub commits (`f7c3a69`, `13b8889`, `36eab65`) across five files
  (the NO and EN section drafts, both assembled drafts, and the .tex).
- Commit `e6d2fa0` removed the material from those files as a **content
  edit** (9 files, +13/-65), not a history rewrite. Git therefore retains
  the deleted content in the pre-scrub blobs; `git show <sha>:<path>`
  recovers it for anyone with repo access.

Consequence: a public push exposes the superseded material from history
even though HEAD is clean.

## Reproduction

```sh
git log --all --oneline -S "<marker>"   # -> f7c3a69, 13b8889, 36eab65
git grep -n -i "<marker>" HEAD          # -> no hits (HEAD clean)
git show --stat e6d2fa0                 # -> content edit, no file removals
```

## Root cause

`e6d2fa0` deleted text from files that remain in the tree. Deleting content
from a file does not remove it from history; only a history rewrite does.

## Alternatives considered (and the argument against acting)

This is an irreversible operation on the project's sole source artifact and
must not be undertaken lightly. The honest case against:

1. **Keep the repo private permanently.** arXiv (preprint) and OSF
   (pre-registration freezes) already expose the publishable work without
   touching history. If a public repo adds nothing the profile needs, the
   safest action is none. — Rejected: the public profile is carried by one
   original repo (`nordeval-skills`) plus forks; chatcat is the strongest
   available original, leader-scale artifact, and its absence is the
   profile's main weakness.

2. **Squash the affected commits.** — Rejected: loses the granular,
   ADR-traceable commit history that is itself part of the paper's
   reproducibility story.

3. **Orphan-branch / fresh repo from current HEAD.** — Rejected: nuclear;
   discards all history, same loss as above, larger.

Mitigating the risk of the chosen path: the repo is private with a single
collaborator, so the usual "force-push breaks every clone" cost is borne by
one local clone (re-clone fixes it), not a team.

## Decision

Rewrite history with `git filter-repo --replace-text` to remove the
superseded material from all historical blobs, then force-push. Proceed
only after the two verification gates below pass on the rewritten clone,
**before** the push.

## Fix path

1. Fresh mirror clone (filter-repo requires a clean clone).
2. Build `expr.txt` (NEVER committed) with the exact strings captured via
   `git show 36eab65:<path>` for the five affected files, replacement empty.
   Use regex with DOTALL for the multi-line subsection block.
3. `git filter-repo --replace-text expr.txt`.
4. Run both verification gates (below). If either fails, stop; do not push.
5. Force-push all refs and tags to origin.
6. Re-clone locally from the rewritten origin.

If `--replace-text` leaves a malformed stub in a historical draft, that is
acceptable — historical draft versions need not be valid; only HEAD must be
correct, and HEAD is untouched.

## Verification gates (both must pass before push)

- **History clean:** `git grep -i "<marker>" $(git rev-list --all)` returns
  nothing for every scrub term, across all refs.
- **HEAD bit-exact:** the rewritten HEAD tree is identical to the
  pre-rewrite HEAD tree (`git diff <old-HEAD> <new-HEAD>` empty). The arXiv
  bundle blob hash is unchanged.

## Consequences

- All SHAs from `f7c3a69` forward change. The handover commit chain
  (`a14ca78 -> ... -> 32b1829`), the title-lock reference (`a9c44f4`), any
  tags, and all SHA references in PK / memories / handover become stale and
  must be updated to the new HEAD after the rewrite.
- Verify nothing external hard-pins a pre-rewrite SHA: OSF freeze `a9mnv`,
  the arXiv submission metadata, and the paper text. If any does, record the
  old->new mapping.
- The superseded material remains available off-repo for the separate future
  work it is reserved for; this operation removes it only from the public
  source history.

## References
- ADR-before-fix discipline; destructive-operation discipline (argue against
  as a mandatory step).
- Read-only history investigation, 2026-06-13.
