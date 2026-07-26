---
description: Drive the current change to a merge-ready PR — reproduce the gates as CI runs them, triage any red correctly, sequence the merge, and stop at green-awaiting-approval.
argument-hint: "[what this change is, in a few words] — optional; inferred from the diff"
---

Run the **ship** loop for the current change.

Load the `ship` skill with the Skill tool and follow it. Do not summarise it
from memory — the failure modes it guards against are exactly the ones that look
reasonable in the moment.

**This change:** $ARGUMENTS

If that is empty, work out what the change is from `git status` and `git diff`
before doing anything else. A commit message written without reading the diff
describes what you intended, not what you are shipping.

Hold to these for this run:

- **Never make a gate pass by weakening it.** Waivers, ignore comments,
  loosened pins, `--no-verify`, deleted tests — all are someone else's decision,
  not this loop's. If the only route to green runs through one, stop and report.
- **Reproduce a gate with CI's own flags** before concluding it is wrongly
  failing. Read the workflow step or the hook's `args`; do not reconstruct the
  command from memory.
- **Work out whose red it is** — yours, pre-existing, or a stale green — before
  editing anything.
- **Stage by name.** Never `git add .` or `-A`.
- **One concern per PR**, plain English throughout, no internal record
  identifiers anywhere in git artefacts.
- **Stop at merge-ready.** Merging is the approver's call, and an approval of an
  earlier change is not an approval of this one.

Finish with the five-line report, including the `Config:` line stating whether
any gate configuration was touched.
