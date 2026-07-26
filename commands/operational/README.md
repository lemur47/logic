# Operational Commands

Slash commands that run *the ritual around the work*, not the work itself.

They pair with the operational skills in
[`../../skills/operational/`](../../skills/operational/README.md): the command is
the thin, invocable entry point; the skill holds the method. Commands live here
so they are version-tracked and reviewable, and are activated by symlink into the
user scope so they are available from **every** repository rather than one.

| Command | Purpose |
|---------|---------|
| [`/boot-ritual`](boot-ritual.md) | Open a session — read shared memory, verify it against repo and tracker ground truth, correct what drifted, classify inbound pull requests, report, and hand into planning or execution. |
| [`/close-ritual`](close-ritual.md) | Close a session — write changes back to shared memory, sweep durable claims for staleness, open a doc pull request if needed, and log a handover the next session or machine can boot from. |

Both invoke the [`session-rituals`](../../skills/operational/session-rituals/SKILL.md)
skill, which keeps universal method in the tracked files and organisation
specifics in a gitignored `CALIBRATION.local.md` overlay — the same
public-logic / private-calibration split used throughout this repository.

## Activation

Symlink into the user scope, once per machine:

```bash
mkdir -p "$HOME/.claude/commands" "$HOME/.claude/skills"

ln -sfn "$HOME/projects/logic/commands/operational/boot-ritual.md"  "$HOME/.claude/commands/boot-ritual.md"
ln -sfn "$HOME/projects/logic/commands/operational/close-ritual.md" "$HOME/.claude/commands/close-ritual.md"
ln -sfn "$HOME/projects/logic/skills/operational/session-rituals"   "$HOME/.claude/skills/session-rituals"
```

User scope, not project scope, is what makes these cross-programme. A
`.claude/skills/` symlink inside one repository is only visible from that
repository, which is the wrong shape for a ritual that serves several.

**Verify rather than assume.** Activation failing quietly — while the documented
remedy reports success — is a mistake this toolchain has already made once.
After linking, start a fresh session and confirm `/boot-ritual` is listed and
`session-rituals` appears in the available skills. A command also only ever fires
when it is invoked; the symlink makes it *available*, not automatic.

## A Note on Scope

These commands read and reconcile. They do not merge pull requests, start
approved work, or change behaviour. The only commit a ritual makes is
documentation, on its own branch, for someone else to merge.
