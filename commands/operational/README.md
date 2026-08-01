# Operational Commands

**These commands have moved to [github.com/lemur47/agent-ops](https://github.com/lemur47/agent-ops)** (public, MIT).

`/boot-ritual`, `/close-ritual` and `/ship` used to live here, paired with the operational skills in
[`../../skills/operational/`](../../skills/operational/README.md). They moved for the same reason those skills
did: they run *the ritual around the work*, not the work itself, and nothing in them depends on this
repository's decision maths. This file stays so that a link from a blog post or an older commit still lands
somewhere useful rather than on a 404.

| Command | Now at |
|---------|--------|
| `/boot-ritual` | [agent-ops `commands/boot-ritual.md`](https://github.com/lemur47/agent-ops/blob/main/commands/boot-ritual.md) |
| `/close-ritual` | [agent-ops `commands/close-ritual.md`](https://github.com/lemur47/agent-ops/blob/main/commands/close-ritual.md) |
| `/ship` | [agent-ops `commands/ship.md`](https://github.com/lemur47/agent-ops/blob/main/commands/ship.md) |

Activation instructions live with the commands, in that repository's README. Two points from them are worth
repeating because they were learned here the expensive way:

**User scope, not project scope, is what makes a ritual cross-programme.** A `.claude/skills/` symlink inside
one repository is only visible from that repository, which is the wrong shape for something serving several.

**Verify rather than assume.** Activation failing quietly — while the documented remedy reports success — is a
mistake this toolchain has already made. After linking, start a fresh session and confirm the command is listed
and its skill appears in the available skills. A command also only fires when it is invoked; a symlink makes it
*available*, never automatic.
