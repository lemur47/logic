---
name: cleanup
description: Staleness sweep across durable-claim surfaces — README, agent instruction files, docs, and shared memory — before a retro, before sprint planning, or after a run of merges. Finds claims that reality has moved past, then corrects them, marks them unverified, or retires them.
---

# Cleanup — Staleness Sweep

Code has tests. Prose has nothing.

A README that describes last month's architecture, an agent instruction file
naming a renamed script, a shared-memory fragment asserting a credential that
was revoked — none of these fail a build. They are read, believed, and acted on.
**Stale-but-trusted is worse than empty**: an empty store makes you go and look,
a confident wrong one does not.

This skill sweeps the surfaces that carry durable claims and reconciles them
against what is actually true now.

## When to run

- **Before a retro** — so the retro reasons about reality, not about the record.
- **Before sprint planning** — briefs written against stale ground truth produce
  stale work, and that cost is paid at execution time.
- **After a run of merges** — several PRs in a short window is exactly when prose
  falls behind code.
- **When a stale claim has just bitten you** — sweep the neighbours; the same
  author, session or assumption usually produced more than one.

Not a routine tidy. If nothing has changed, this finds nothing and should be
cheap to conclude.

## What counts as a durable-claim surface

Anything read as authoritative by a future reader — human or agent — that no
test verifies:

1. **Entry-point docs** — README and equivalents. First contact; wrong here is
   expensive.
2. **Agent instruction files** — loaded into context automatically, so errors
   propagate silently into work rather than being noticed on read.
3. **Design and strategy docs** — the "why", which decisions quietly supersede.
4. **Shared memory / knowledge stores** — the highest-risk surface, because it is
   consulted at session boot and rarely re-read critically.

The organisation's specific paths, namespaces and owners belong in
`CALIBRATION.local.md` alongside this file, not here.

## Method

### 1. Establish what actually changed

Start from evidence, not from re-reading everything:

```
git log --oneline <since>..HEAD
git diff --stat <since>..HEAD
```

Renames, deletions and moved responsibilities are the highest-yield signals —
they orphan references without breaking anything.

### 2. Grep for claims the change invalidates

For each notable change, search every durable surface for the **old** name,
path, number or state. A rename is not done until nothing still points at the
old name — and the search must cover surfaces outside the repo, which no CI job
can reach.

### 3. Triage — old is not the same as stale

Only two questions matter:

- **Is it false now?** Not "was it written a while ago".
- **Would a reader act on it?** A load-bearing claim outranks a stylistic one.

Fix false and load-bearing first. Leave accurate-but-old alone; churn costs
review attention and buys nothing.

**Verify before rewriting.** A claim that *looks* stale may be correct, and a
claim that looks fine may assert external state that drifted silently —
credentials, expiry dates, service bindings, third-party behaviour. Check the
external ones against the world, not against the document.

### 4. Distinguish record from reference

Some prose is a **historical record** — a changelog, a sprint history, a note
describing what was true at a point in time. Correcting it to present reality
**falsifies history**. Leave it and, if it misleads, annotate alongside rather
than overwrite.

The test: does this text claim *"this is how things are"* or *"this is what
happened"*? Only the first is in scope.

### 5. Correct, mark unverified, or retire

Three dispositions, in order of preference.

**Correct it.** Where the truth is known, fix it and say what changed.

**Mark it unverified.** Where the truth cannot be established now, say so *in
the document*. A claim labelled unverified is safe; the same claim stated
plainly is a trap. This is the single highest-value output of a sweep — most
damage comes from confident staleness, not from absence.

**Retire it.** A fragment that is wholly superseded and carries no historical
value should be deleted, not left to rot. A knowledge store that only ever
grows becomes a store nobody reads, and an unread store is one nobody notices
is wrong.

Deletion is the only irreversible action in a sweep, so the bar is high. Retire
only when **all** of these hold:

- **Wholly superseded** — every claim in it is either false now or restated
  somewhere current. If any part is still uniquely true, correct it instead.
- **Not a record.** See step 4. Plans, seeds and retros describing what was
  decided at a point in time are history, however finished the work is.
- **No inbound references.** Search the store for links to it first; deleting a
  linked fragment turns a useful pointer into a dead end. Update the referrers
  in the same pass, or do not delete.
- **Its lesson is preserved.** If the fragment recorded a mistake worth not
  repeating, that lesson moves somewhere durable before the fragment goes.

When in doubt, prefer correcting. A short, accurate fragment costs almost
nothing to keep; a deletion that loses the only record of why something is the
way it is cannot be undone.

The store's deletion facility is named in `CALIBRATION.local.md` — it differs
per organisation, and naming it here would tie a universal method to one vendor.

### 6. Report

State what was checked, what changed, what was deliberately left, and what could
not be verified. A sweep that reports "nothing stale" without saying what it
examined is indistinguishable from one that did not run.

## What not to do

- **Do not rewrite history.** See step 4.
- **Do not sync documents that are allowed to differ.** Teaching copies,
  worked examples and vendored snapshots often diverge by design. Check whether
  a divergence is declared before treating it as drift.
- **Do not churn.** Rewording accurate prose creates review load and buries the
  corrections that matter.
- **Do not fix code here.** If the sweep finds a defect, flag it as its own
  piece of work. A staleness sweep that quietly changes behaviour is
  unreviewable.

## Why this keeps happening

Documentation drifts for the same reason duplicated code diverges: two things
describe one truth, and nothing forces them to agree. Code at least has tests.
Prose has this sweep — which is why it must be deliberate and periodic rather
than assumed.
