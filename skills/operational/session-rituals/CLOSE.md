# Close Phase

Write back what this session moved, correct the durable claims it invalidated,
and leave a handover that a different session — or a different machine — can
boot from without asking anyone.

Read [`SKILL.md`](SKILL.md) first. Resolve the programme and load its row from
`CALIBRATION.local.md` before step 1.

## 1. Establish What This Session Changed

Evidence, not recollection:

```
git log --oneline <session-start>..HEAD
git status --short
gh pr list --state all --limit 10
```

Plus the tracker: which items changed status, and which decisions were taken.

Renames, deletions and moved responsibilities are the highest-yield signals —
they orphan references without breaking anything, so nothing fails and nobody
notices.

If nothing changed, the close is cheap and should conclude quickly. Say so and
go to step 5; do not manufacture updates.

## 2. Write Back to the Memory Layer

For each fragment whose claims this session moved, update it — and **rewrite the
hook**, not just the body. The hook is the whole index; a fragment whose hook
still advertises last week's state is stale however accurate its body is.

Three things to get right:

- **State the disposition, not just the fact.** "Shipped", "closed", "corrected",
  "still open, blocked on X" tells the next boot what to do. A bare fact does not.
- **Record corrections as corrections.** When this session proved an earlier
  fragment wrong, say so in the fragment and say what the old claim was. A
  silently-fixed fragment teaches nobody, and the same mistake returns.
- **Retire what is wholly superseded**, to the bar the
  [`cleanup`](../cleanup/SKILL.md) skill sets — which is high, and which requires
  the fragment's lesson to be preserved elsewhere first. When in doubt, correct
  instead. A store that only grows becomes one nobody reads, and an unread store
  is one nobody notices is wrong.

## 3. Sweep for Doc Staleness

Do not improvise a second staleness method. Invoke the
[`cleanup`](../cleanup/SKILL.md) skill and scope it to this session's changes.

The surfaces that always warrant a look, because they are read as authoritative
and no test covers them:

- **Entry-point docs** — the README and its equivalents. First contact, so wrong
  here is the most expensive kind of wrong.
- **Agent instruction files** — loaded into context automatically, so an error
  propagates silently into work instead of being noticed on read. Includes the
  local, uncommitted overlays.
- **Design, strategy and architecture docs** — the "why", which decisions
  quietly supersede.

Use the last recorded sweep floor as `<since>` if the register names one. If no
floor exists, this sweep establishes one, and the report must say the programme
had never been swept.

## 4. Open a Doc Pull Request

If the sweep found corrections that touch tracked files:

1. Branch — never commit to the default branch. If a commit has landed there by
   accident, recover by repointing the branch at the remote rather than
   discarding the working tree.
2. Commit the doc corrections **alone**. Doc-only, separate from feature work,
   so the diff is reviewable at a glance. Let the repository's own gates run —
   a classification or secret gate exists precisely to catch what a close-phase
   commit is most likely to carry, and bypassing it here is the worst possible
   moment to start.
3. Open the pull request. Describe the work in plain English; no tracker record
   identifiers anywhere in the branch name, title, message or body.

Uncommitted local overlays are corrected in place — they are not in the pull
request, so say in the report that they changed.

If the sweep found nothing to commit, say that rather than opening an empty one.

## 5. Log the Handover

The step that makes the next boot cheap. Append — never overwrite — to the
programme's session or sweep log, as named in the register.

Include only what a reader who was not here cannot reconstruct:

- **What was done**, in one line, with the pull requests.
- **What is in flight**, and what it is waiting on. Name the owner: this session,
  the approver, another machine, an external party.
- **The floor for the next sweep** — the commit the next sweep starts from.
  Without it, the next sweep either re-reads everything or guesses.
- **What was learned**, if a lesson cost something to acquire. A lesson written
  once and never enforced tends to recur, so say plainly whether it is now
  mechanically enforced or still only written down.

**Cross-machine items go where the other machine boots from**, not only in this
programme's namespace. A handover left in a namespace the recipient never reads
is not a handover. If the recipient boots from a different programme, write it
there and cross-reference.

## 6. Report

Six lines. Same discipline as the boot report.

```
CLOSE — <programme> · <repo>@<branch> · <date>
Shipped:  <PRs merged / opened, or none>
Memory:   <n> updated · <n> retired · log appended at <ref>
Docs:     <clean | PR #n — files>
Handover: <what the next session or machine picks up, and who owns it>
Open:     <unresolved, with owner — or none>
```

Below the block, at most one short line per unresolved item. Nothing else.

## Do Not

- **Do not overwrite an append-only field.** Retrospectives, sweep logs and
  shared narrative fields have more than one author. Re-read immediately before
  appending, and label the block.
- **Do not rewrite history to match the present.** A note describing what was
  true at a point in time stays as it is; if it now misleads, annotate alongside.
- **Do not merge the doc pull request.** The approver's merge is the gate, and
  that is as true for a two-line correction as for a feature.
- **Do not close over a red gate or an unresolved blocker silently.** It goes on
  the `Open:` line with an owner, or the session does not close.
