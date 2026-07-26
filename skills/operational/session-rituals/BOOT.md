# Boot Phase

Load the memory layer, prove it against ground truth, absorb what arrived while
you were away, and hand the session a starting point.

Read [`SKILL.md`](SKILL.md) first — precedence, triage and the guardrails apply
throughout. Resolve the programme from the working directory and load its row
from `CALIBRATION.local.md` before step 1.

## 1. Read the Memory Layer

Read in the order the register gives, which is always broad to narrow: the
manifest or boot index first, then the operating model and product ground
truth, then the stream fragments relevant to the work in hand.

Then list the index. The index is cheap and carries every fragment's `updated`
timestamp and hook — that is the staleness signal. A fragment whose hook
describes a state the repository moved past is a correction candidate; note it
and carry on reading rather than stopping to fix.

Do not read every fragment body. The hooks exist so you do not have to.

## 2. Establish Ground Truth

Only after reading — so that the store's claims are checked, not merely
confirmed by what you happened to look at.

```
git status --short && git branch --show-current
git log --oneline -15
gh pr list --state open
gh run list --limit 5
```

Then the tracker: the current sprint, and the work items by status. Approved and
in-flight work is the tracker's answer, not the store's.

Note whether the working tree is clean and whether the branch is the default
one. A stray commit on the default branch is a finding, not a detail.

## 3. Reconcile

For each candidate from step 1, apply precedence from `SKILL.md` and decide.

**Correct in place** where the truth is now known. Rewrite the fragment's hook
as well as its body — the hook is what the next boot reads first, so a corrected
body under a stale hook is still a stale fragment.

**Mark unverified** where the truth cannot be established from here. External
state, another machine's work, anything needing a credential you do not hold.

**Append, never overwrite,** on records. See the rule in `SKILL.md`.

Count the corrections. If the count is high, that is itself the finding: the
previous session skipped its close, and the report should say so.

## 4. Check What Arrived

Work that appeared without anyone deciding to start it:

- **Dependency pull requests** — automated bumps accumulate quietly and go red
  quietly. For each: does it touch a lockfile the gates actually scan, is it a
  major bump, does it carry an advisory?
- **Stale green checks.** A pull request's green tick records that the gates
  passed *then*. The question before any merge recommendation is whether they
  would pass *now* — advisory feeds move underneath an untouched branch, so a
  check more than a few hours old is not evidence. Treat it as unknown and say
  so rather than reporting it as green.
- **Failing gates on the default branch** — a red main is the only genuinely
  blocking find in a boot, and it outranks whatever the session was for.
- **Security advisories** against the tree, and any waiver approaching expiry.
- **Review-state work** — items the tracker says are finished but which no
  merged pull request supports, or the reverse.

Classify each into exactly one of: **mergeable as-is**, **needs its own piece of
work**, **blocking**. Classify only. Merging is not a boot action, and neither is
opening the work item — mid-session needs are flagged, then folded into planning
unless the approver says otherwise.

## 5. Report

Six lines. Use this shape; omit nothing, and say "none" rather than dropping a
line.

```
BOOT — <programme> · <repo>@<branch> · <date>
Memory:   <n> read · <n> corrected · <n> unverified
Repo:     <last commit> · <clean | n changes> · gates <state>
Work:     <sprint> · <n in progress> / <n review> / <n backlog>
Inbound:  <n PRs (n automated)> · <blocking, or none>
Next:     <the single thing this session should start with>
```

Below the block, at most one short line per correction — what was wrong, what it
says now. If there were none, say so on one line. Nothing else.

## 6. Hand Off Into the Session

State which of the two the session is, and say why:

- **Planning** — the sprint has no approved slate, or the slate is finished. The
  boot findings are inputs to it, and the author-reviewer separation still
  applies: a fresh reviewer with no authoring context checks the briefs.
- **Execution** — there is approved, in-flight work. Name the item, confirm its
  dependencies are met, and start from the brief as written.

If the boot turned up something blocking, neither starts until it is resolved or
explicitly deferred by the approver.

## Do Not

- **Do not merge, and do not start approved work from inside the boot.** The boot
  produces a decision; the session acts on it.
- **Do not fix code.** A defect found at boot is flagged, not patched. A ritual
  that quietly changes behaviour is unreviewable.
- **Do not skip the read because the session feels like a continuation.** The
  cost of a skipped boot is paid later, by a session that re-derives a lesson
  already written down.
