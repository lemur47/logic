---
name: content-cadence
description: Pipeline for turning one R&D artefact (PR, PoC, analysis) into one public post — briefing or deep dive — plus a LinkedIn derivative. Triggers when an R&D output is ready to become content, or when drafting any blog post for the site. Enforces the anonymisation gate and repo editorial conventions.
---

# Content Cadence

Every R&D artefact worth publishing feeds **one** post — a briefing *or* a deep dive, never both — and that post feeds **one** LinkedIn derivative. This skill encodes the cadence, the two post frames, and the gates a draft must pass before it moves toward a public surface.

```
R&D artefact (PR, PoC, analysis)
      ↓  choose ONE frame
Briefing  |  Deep Dive        (EN + JA, same slug)
      ↓
LinkedIn derivative           (delivered to the publisher, not committed)
```

> **This skill is organisation-neutral.** Audience, voice, publishing channels, and sign-off owners live in a co-located `CALIBRATION.local.md` overlay (gitignored), following the same pattern as the [anonymisation](../anonymisation/SKILL.md) skill. The frames, gates, and conventions below are universal.
>
> **If the overlay is absent**, do not halt: derive audience and voice from the existing posts in the blog content directory, treat the person requesting the draft as the sign-off owner, and flag the missing overlay in the handover so it gets created.

## Inputs

One R&D artefact per run. Acceptable inputs:

- A merged PR or shipped feature (link + diff context).
- A standalone PoC (`examples/` directory or equivalent).
- An analysis or investigation with a conclusion (retro finding, benchmark, calibration result).

If the artefact has no conclusion yet, stop — content follows the work, it does not precede it.

## Choosing the Frame

| Signal | Frame |
|--------|-------|
| The reader needs a decision-ready summary; the finding matters more than the method | **Briefing** |
| The method is the value: data, models, and reasoning the reader will reuse | **Deep dive** |
| Time-sensitive context (a change in the landscape the audience should act on) | **Briefing** |
| Evergreen reference the audience will return to | **Deep dive** |

One artefact, one frame. If both seem to fit, ship the briefing now; a deep dive can be a *separate future artefact* with new material, not a same-week rerun.

## Section Taglines

Both frames use tagline-bearing headings: every H2 carries a single sentence stating that section's takeaway, so a reader skimming only headings still gets the whole argument. Write the tagline *after* the section — it is the section's conclusion, not its topic.

## Frame 1 — Briefing

Short, decision-first. The finding matters more than the method.

```markdown
## Key Judgements: <tagline>
## Situation: <tagline>
## Analysis: <tagline>
## Evaluation: <tagline>
## Recommendation: <tagline>
```

- **Key Judgements** — the conclusions up front, stated as judgements the reader can act on.
- **Situation** — what happened and why the reader should care now.
- **Analysis** — the evidence: what the artefact showed.
- **Evaluation** — what the evidence means; weigh options and risks.
- **Recommendation** — what to do next, concretely.

## Frame 2 — Deep Dive

Long-form, method-first. The title itself carries a tagline — `<title>: <tagline>` — and the sections keep the same tagline discipline as a briefing.

```markdown
## Executive Summary: <tagline>
## Situation: <tagline>        (or "Problems:" — choose whichever fits the piece)
## Analysis: <tagline>
## Evaluation: <tagline>
## Recommendation: <tagline>
```

- **Executive Summary** — the whole argument in one screen.
- **Situation or Problems** — the problem class, framed for the reader's context. Pick one heading, not both.
- **Analysis** — data, industry base rates, and systems analysis of the problem.
- **Evaluation** — leverage points, supported by feedback loops and an iceberg analysis tailored to the case.
- **Recommendation** — which leverage points to take on first, and how.

## Editorial Conventions (Binding)

- **British English** throughout the EN post (analyse, colour, maths).
- **APA 7th title case** for H1 and H2 headings.
- **Slugs and tags are English-only**; EN and JA posts share the same slug for i18n routing (`site/src/content/blog/en/<slug>.md` and `site/src/content/blog/ja/<slug>.md`).
- **Frontmatter** per the site schema: `title`, `description`, `pubDate`, `tags` (all required); `draft` and `contentType` optional.
- **Frontmatter values:** set `contentType` to `"briefing"` or `"deep-dive"` to match the frame; `description` is one or two plain sentences in the post's register; `pubDate` is the drafting date, paired with `draft: true` until the publish decision (publishing is outside this skill).
- **Slug:** short kebab-case drawn from the title's key noun phrase, roughly two to six words.
- **Title case vs. taglines:** the heading label before the colon is APA title case; the tagline after the colon is a normal sentence in sentence case (proper nouns and brand casing kept as-is). A deep dive's `<title>: <tagline>` follows the same split. A briefing's title is a plain title — no tagline required.
- **JA is a native rewrite, not a translation.** Prefer native terms over katakana transliterations (経験則 not ヒューリスティック, 価値 not ベネフィット); restructure sentences for JA rhythm rather than mirroring EN syntax.

## Gates (Must Pass Before Review)

1. **Anonymisation — binding.** Run the [anonymisation](../anonymisation/SKILL.md) skill over the full draft (EN, JA, and LinkedIn derivative) before anything moves toward a public surface. Its decision procedure applies paragraph by paragraph; if an example cannot be scrubbed, drop it for an industry baseline. **Fast pass:** if no paragraph draws on real client or engagement experience (e.g. the artefact is the organisation's own public code), the gate passes — note "anonymisation: no engagement material" in the handover and move on.
2. **Image references.** Every inline image `![...](path)` in both posts must resolve to a real committed file (e.g. `/blog/foo.png` → `site/public/blog/foo.png`). Grep and verify each one; missing assets block review — request them, do not ship without. The LinkedIn derivative is exempt (it is not committed; any image is attached at publish time).
3. **Frame integrity.** Every H2 (and a deep dive's title) carries its tagline. Skimming headings alone must convey the argument.

## Outputs

| Artefact | Destination |
|----------|-------------|
| EN post draft | `site/src/content/blog/en/<slug>.md` |
| JA post draft | `site/src/content/blog/ja/<slug>.md` |
| LinkedIn derivative | Delivered to the publisher in-conversation; not committed to the repo |

The LinkedIn derivative is a compression of the post, not a teaser: lead with the strongest judgement, one supporting point, and a link to the post. It passes the same anonymisation gate.

## Procedure

1. Ingest the artefact; extract the finding, the evidence, and who it serves.
2. Choose the frame (table above); record the choice and the reason in the handover notes that accompany the draft (for this repo: the Work Item report).
3. Draft the EN post in the chosen frame, following the editorial conventions; write each section's tagline after drafting the section (it is the conclusion, not the topic).
4. Run gate 1 (anonymisation) on the EN draft; rewrite or drop failing paragraphs.
5. Write the JA post as a native rewrite of the gated EN draft.
6. Write the LinkedIn derivative from the gated post.
7. Run all three gates end to end; fix or escalate anything failing.
8. Hand the drafts over for review — publishing is a separate decision, outside this skill.
