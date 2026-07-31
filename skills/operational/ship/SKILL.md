---
name: ship
description: Drive a change from working tree to a merge-ready pull request — reproduce the gates exactly as CI runs them, triage reds correctly, and sequence the merge. Use when committing, pushing, opening a PR, or when a pre-commit hook or CI check has gone red and you need to decide whether to fix, defer, or stop. Terminates at green-awaiting-approval; it never merges.
---

# Ship — Commit to Merge-Ready

A repository with good gates does not need an agent to invent checks. The
checks exist, they are deterministic, and they are the same every time.

What costs time is everything around them:

- **Reproducing a gate wrongly**, and drawing a confident conclusion from the
  wrong answer.
- **Triaging a red that is not yours** — deciding between fix, defer, and stop.
- **Sequencing** — which pull request merges first, and what must be updated
  after it does.

This skill is those three things. It is not a licence to make checks pass.

## The One Rule That Matters Most

> **Never make a gate pass by weakening the gate.**

An automated loop optimises for "the check is green". In a repository whose
gates are security controls, the cheapest route to green is almost always to
lower the bar — and every one of those routes looks like a fix:

| Looks like a fix | Actually is |
|---|---|
| Adding an ignore/waiver entry for the finding | Deleting the finding |
| Extending a waiver's review-by date | Making a deferral permanent |
| Adding a lint or type ignore comment | Hiding the defect |
| `--no-verify`, `--force`, skipping a hook | Removing the control entirely |
| Loosening a version pin to resolve a conflict | Trading a known-good for an unknown |
| Deleting or skipping the failing test | The worst of all of these |

Every one of these may occasionally be the right answer. **None of them is ever
this loop's call.** They are a separate, explicitly approved piece of work, with
their own reasoning written down. If the only way to green is through that
table, the loop has finished: report and stop.

The corollary is that a green result is only meaningful if you did not touch the
thing measuring it. Say in the report whether any gate configuration changed.

## Reproduce the Gate Exactly

Before concluding anything about a check — especially that it is *wrongly*
failing — run it the way CI runs it.

**Read the invocation; do not recall it.** The flags live in the workflow file
and the pre-commit config. Reconstructing a command from memory produces
something that looks equivalent and is not.

This is not hypothetical. A scanner run without its `--config` flag loaded the
project's suppression file, reported every entry in it as *unused*, and then
failed on those same suppressions — an exact impersonation of expired waivers.
Acting on that reading would have "fixed" a control that was working correctly.

So:

1. Find how CI invokes the tool (the workflow step, the hook's `args`).
2. Run that, verbatim, including config flags and working directory.
3. Only then interpret the result.

Where a local hook and CI disagree about scope — different file sets, different
lockfiles, different stages — trust neither until you have run the wider one.
A local pass is not evidence that CI will pass.

## What Cannot Be Read Off the Repository

Most of what this loop needs is **discovered, not configured**: the gate
invocations are in the workflow files and the hook config, and reading them is
the point of the section above.

Three things are not discoverable, and they are the ones that decide the report —
**who approves a merge**, **which checks are required rather than merely
present**, and **the traps that have already cost time here**. Those are
organisation-specific and belong in a calibration overlay, never in this file.
Resolve it in this order and take the first hit:

1. `<repo>/.claude/calibration/ship.local.md` — a repository carrying its own
2. `~/.claude/calibration/operational.local.md` — the machine-wide register,
   serving every programme worked on from this machine
3. `CALIBRATION.local.md` beside this file — a single-programme overlay

Rung 2 is the usual home. A single-repo overlay is the shape this skill is most
likely to get wrong, because ship is invoked *from* a repository and an overlay
sitting beside the skill looks local when it is not: run the loop in a second
repository and it silently applies the first one's required-context list and
approval authority.

**If no overlay resolves, run the loop but do not report merge-ready.** The
gates can still be reproduced from the repository — that part is honest work —
but "green on the required set, awaiting the approver" is a claim about a set
and an authority you do not have. Say which you are missing.

## The Loop

### 1. Pre-flight

Confirm the branch is not the default one, and that the working tree contains
only the change you mean to ship. If a commit has landed on the default branch
by accident, repoint the branch at the remote rather than discarding the tree.

Stage files **by name**. Never `git add .` or `-A` — untracked noise and local
overlays live alongside the work, and a gitignored file is only one `.gitignore`
edit away from being staged by a wildcard.

### 2. Commit, and let the hooks run

The pre-commit chain is the fastest feedback available; a red here costs seconds
and a red in CI costs minutes. Read what actually failed rather than the summary.

If a hook rewrites files (formatters commonly do), **re-stage and re-run**. A
commit that succeeds while its formatted output sits unstaged ships the
unformatted version.

### 3. Triage the red — whose is it?

Three cases, three different actions:

- **Yours.** The change caused it. Fix it, subject to the rule above, and re-run.
- **Pre-existing.** The default branch is already red, and your change cannot
  have caused it — a lockfile you did not touch, a scanner rule that moved. Do
  **not** silently absorb it into this change: that buries a real problem inside
  an unrelated diff. Report it, and let the approver choose between fixing it
  first as its own change, bypassing with the deviation recorded, or stopping.
- **Stale, not red.** A check that passed hours ago is evidence about *then*.
  Advisory feeds move under untouched branches. Report an old green as
  **unknown**, never as green.

Establish which case you are in *before* editing anything. The cost of guessing
wrong is an unreviewable diff.

### 4. Push and open the pull request

Describe the work in plain English. Keep internal record identifiers out of the
branch name, commit message, title and body — git history is the external record
and cannot be edited after the fact.

One concern per pull request. If the branch has grown a second concern, split it;
combining them buys nothing and costs review attention.

### 5. Watch CI without burning turns

Wait event-driven rather than by polling on a timer. Emit on **every** terminal
state, not just success — a watcher that greps only for the happy path is silent
through a crash, and silence is indistinguishable from still-running.

Re-triage any red with step 3. A check that failed locally and passes in CI (or
the reverse) is itself a finding about gate fidelity — say so.

### 6. Sequence the merge

Under strict up-to-date branch protection, order matters:

1. If a prerequisite pull request exists (a dependency bump that clears a gate
   this one needs), it merges first.
2. Update this branch from the default branch.
3. Wait for the **full** required set to re-run. The previous green is void.
4. Report merge-ready.

Checks that are required and checks that merely exist are different sets. Know
which is which before calling something blocking — a preview deploy on a change
that touches no deployable file is noise, not a gate.

### 7. Stop

**The loop terminates at green-awaiting-approval.** Merging is the approver's
step, and that is as true for a two-line documentation fix as for a feature.
Do not merge, and do not treat a previous approval of a different change as
approval of this one.

## Report

```
SHIP — <branch> → <PR #n or "not opened">
Gates:    <local: pass/fail> · <CI: n/n required>
Reds:     <what failed, whose it was, what was done — or none>
Config:   <any gate config touched — or "untouched">
Blocked:  <what stops the merge, and whose call it is — or "merge-ready">
```

The `Config:` line is not optional. A green report from a run that also edited a
waiver, a pin or an ignore rule means something quite different from one that
did not, and the reader cannot tell from the other lines.

## Do Not

- **Do not merge.** See step 7.
- **Do not weaken a gate.** See the rule above.
- **Do not bundle an unrelated fix** into the change to get it green.
- **Do not report a gate as clear on a partial run.** Say which invocation you
  used, so the claim can be checked.
- **Do not retry a bypass that was declined.** A refused `--no-verify` is an
  answer, not an obstacle.
