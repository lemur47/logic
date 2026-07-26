---
name: session-rituals
description: Open or close a programme working session — reconcile shared memory against repo and tracker ground truth, sweep for staleness, and hand over. Use for the boot ritual (start of session — read memory, verify against the working tree and the work tracker, check inbound PRs, report and prepare sprint work) and for the close ritual (end of session — write findings back, check doc staleness, open a doc PR, log the handover). Triggers on /boot-ritual, /close-ritual, "boot the session", "close the session", "session handover".
---

# Session Rituals — Boot and Close

A programme's knowledge lives on four surfaces that nothing forces to agree:
the working tree, the work tracker, the shared memory store, and the agent
instruction files. Code has tests. The agreement between these four has only
this ritual.

The failure is asymmetric. An **empty** store makes you go and look; a
**confidently wrong** one does not — it is read at boot, believed, and acted on.
So the store's job is not to accumulate. It is to stay true, and to say so when
it cannot.

Two phases, one model:

- **Boot** — load the store, verify it against ground truth, correct what
  drifted, surface what arrived while you were away, then start work from
  reality. See [`BOOT.md`](BOOT.md).
- **Close** — write back what this session moved, sweep the durable claims it
  invalidated, and leave a handover a different session or a different machine
  can boot from. See [`CLOSE.md`](CLOSE.md).

Skipping close is what makes the next boot expensive. Skipping boot is what
makes the next session re-derive a lesson it already paid for.

## The Surface Register

Every programme this ritual serves is described by one row: which repository is
its ground truth, which memory namespace it boots from, which tracker holds its
approved work, and which files carry its durable claims.

That register is organisation-specific and lives in `CALIBRATION.local.md`
alongside this file — namespaces, tracker identifiers, base and table
identifiers, and machine ownership are not universal method and must not be
committed. **If the overlay is missing, stop and say so.** Guessing a namespace
writes memory nobody will read again; guessing a tracker filter silently returns
nothing and looks like "no open work".

Resolve the programme from the working directory before anything else. If the
directory maps to no row, or to more than one, ask rather than assume.

## Precedence — Which Surface Wins

The store is a cache with no invalidation. When surfaces disagree, this is the
order:

| Question | Authoritative surface |
|---|---|
| What the code, config or pipeline actually does | the working tree at `HEAD`, and the remote's checks |
| What work is approved, in flight, or done | the work tracker |
| Why a choice was made, and what it ruled out | the decision record |
| Anything else — context, pointers, lessons, external state | the shared memory store |

Two consequences worth stating plainly:

- **The store loses by default.** A store claim that contradicts the tree or the
  tracker is stale until proven otherwise, and correcting it is the boot phase's
  main job.
- **The store loses by default, not always.** It is the *only* surface that can
  record external state — a revoked credential, a third-party behaviour change, a
  decision taken in conversation and never committed. When a store fragment
  asserts something the repo simply has no opinion on, the repo is not evidence
  against it. Check that class against the world, not against the tree.

## Drift Triage

Age is not staleness. Only two questions decide:

- **Is it false now?**
- **Would a reader act on it?**

Fix false and load-bearing first. Rewording accurate prose buys nothing and
buries the corrections that matter.

Three dispositions, in order of preference — **correct**, **mark unverified**,
**retire**. The [`cleanup`](../cleanup/SKILL.md) skill owns this method in full,
including the bar for retirement; do not restate or soften it here. The close
phase delegates to it rather than improvising a second version.

One rule this ritual adds, because it is where session work goes wrong:

> **Records are append-only.** A sweep log, a retrospective, a sprint history, a
> handover note — anything answering *"this is what happened"* rather than
> *"this is how things are"* — is corrected by appending a labelled block, never
> by overwriting. Shared narrative fields usually have more than one author, so
> re-read immediately before appending; an overwrite silently deletes another
> party's contribution.

## The Reporting Contract

Both phases end in a **short, fixed-shape report** — a handful of lines, not a
narrative. Each phase file gives its own shape; hold to it.

Brevity is the point. A ritual whose output has to be read carefully will be
skimmed, and a skimmed ritual is a skipped one. Detail belongs in the store,
where it can be read on demand; the report exists only to say what changed and
what to do next.

Two things the report must never do:

- **Claim a surface was checked when it was not.** "Nothing stale" without
  naming what was examined is indistinguishable from not having run.
- **Bury a blocker in prose.** Anything that stops work gets its own line.

## Guardrails for Both Phases

- **The ritual reports and reconciles. It does not ship.** Do not merge pull
  requests, start approved work, or change behaviour from inside a ritual. The
  boot phase's output is a decision for the session; the close phase's only
  commit is documentation.
- **Never commit to the default branch.** Any correction that touches the
  repository goes on its own branch and through a pull request, doc-only and
  separate from feature work.
- **Keep tracker record identifiers out of git artefacts.** Identifiers belong
  in the tracker, in shared memory, and in the overlay — never in commit
  messages, branch names, pull request titles or bodies, or committed file
  content. Refer to work in plain English.
- **Correct in place, but verify first.** Both phases are licensed to fix the
  store without asking. That licence depends on having checked the claim against
  an authoritative surface, and on the fragment not being a record.
- **Report what could not be verified.** An unverified claim that is labelled is
  safe. The same claim stated plainly is a trap.
