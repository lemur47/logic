---
name: content-cadence
description: Pipeline for turning one R&D artefact (PR, PoC, analysis) into one public post — briefing or deep dive — plus a social derivative where the overlay scopes one in. Triggers when an R&D output is ready to become content, or when drafting any blog post for the site. Enforces the anonymisation gate and repo editorial conventions.
---

# Content Cadence

Every R&D artefact worth publishing feeds **one** post — a briefing *or* a deep dive, never both — and — where the calibration overlay puts social derivatives in scope — that post feeds **one** derivative. Drafting starts only once the sign-off owner has stated a content requirement; the artefact supplies the evidence, the requirement supplies the angle. This skill encodes the cadence, the two post frames, and the gates a draft must pass before it moves toward a public surface.

```
R&D artefact (PR, PoC, analysis)
      ↓
Content requirement            (from the sign-off owner: angle, audience, expectation)
      ↓  choose ONE frame
Briefing  |  Deep Dive        (EN + JA, same slug; diagrams/images where they clarify)
      ↓  PR = human-in-the-loop review gate
Social derivative             (only if the overlay scopes it in; not committed)
```

> **This skill is organisation-neutral.** Audience, voice, publishing channels, sign-off owners, and **which artefact classes get a social derivative at all** live in a co-located `CALIBRATION.local.md` overlay (gitignored), following the same pattern as the [anonymisation](../anonymisation/SKILL.md) skill. The frames, gates, and conventions below are universal.
>
> **If the overlay is absent**, do not halt: derive audience and voice from the existing posts in the blog content directory, treat the person requesting the draft as the sign-off owner, and flag the missing overlay in the handover so it gets created.

## Inputs

Two inputs per run — an artefact and a requirement. Drafting needs both.

**1. One R&D artefact.** Acceptable inputs:

- A merged PR or shipped feature (link + diff context).
- A standalone PoC (`examples/` directory or equivalent).
- An analysis or investigation with a conclusion (retro finding, benchmark, calibration result).

If the artefact has no conclusion yet, stop — content follows the work, it does not precede it.

**2. A content requirement from the sign-off owner.** The requirement states, at minimum:

- **Discussion point** — the question the post answers.
- **Perspective** — the angle and the audience's frame (e.g. investment and ROI, not implementation detail).
- **Expectation** — what the finished piece should do for the reader.
- Optionally: current problems observed, and references to draw on.

If no requirement has been stated, request one before drafting — do not infer it from the artefact alone. A technically faithful post written without the requirement routinely misses the audience (this rule exists because it happened). The requirement owner is named in the calibration overlay; absent an overlay, it is whoever requested the draft.

## Choosing the Frame

| Signal | Frame |
|--------|-------|
| The reader needs a decision-ready summary; the finding matters more than the method | **Briefing** |
| The method is the value: data, models, and reasoning the reader will reuse | **Deep dive** |
| Time-sensitive context (a change in the landscape the audience should act on) | **Briefing** |
| Evergreen reference the audience will return to | **Deep dive** |

One artefact, one frame. If both seem to fit, ship the briefing now; a deep dive can be a *separate future artefact* with new material, not a same-week rerun.

## Diagrams and Images

Include a diagram or image when it clarifies the argument — a contrast, a flow, a market map — not as decoration. Conventions:

- Hand-authored SVG committed under the site's public blog assets, in a per-slug directory (for this repo: `site/public/blog/<slug>/<name>.svg`), matching the visual style of existing post diagrams.
- One SVG serves both language versions; the EN and JA posts each carry their own descriptive alt text.
- Keep labels few and legible — a diagram that needs small fonts to fit its labels is carrying too much.
- Every reference must pass gate 2 (image references resolve to committed files).

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
- **Frontmatter values:** set `contentType` to `"briefing"` or `"deep-dive"` to match the frame; `description` is one or two plain sentences in the post's register; `pubDate` is the drafting date.
- **Do NOT set `draft: true`.** The merge is the publish decision (see the review gate below), so the draft flag has no step left to gate — it only creates a second pull request to clear it. Worse, this site excludes drafts from the blog index and the post route in any production build, and a deploy preview *is* a production build: setting the flag hides the post from the very review the pull request exists to enable. No post in this repo carries the field. **This rule exists because it happened** — a briefing shipped with `draft: true` and the preview rendered a blog index that simply did not contain it.
  *If you are adapting this skill to another site:* the flag is only safe where drafts render in preview (e.g. the build sets `PUBLIC_SHOW_DRAFTS`, or previews run in dev mode). Check that before using it; otherwise follow the rule above.
- **Slug:** short kebab-case drawn from the title's key noun phrase, roughly two to six words.
- **Title case vs. taglines:** the heading label before the colon is APA title case; the tagline after the colon is a normal sentence in sentence case (proper nouns and brand casing kept as-is). A deep dive's `<title>: <tagline>` follows the same split. A briefing's title is a plain title — no tagline required.
- **JA is a native rewrite, not a translation.** Prefer native terms over katakana transliterations (経験則 not ヒューリスティック, 価値 not ベネフィット); restructure sentences for JA rhythm rather than mirroring EN syntax.
- **Bold marks the answer, not emphasis.** Bold only the discussion point's answer and the elements that lead directly to it — expect roughly one per section, not one per paragraph. Emphasis works by contrast, so a page where every paragraph carries a bold phrase has no emphasis at all; the reader skims the bold, finds it uniformly important, and stops trusting it. Section taglines and list structure already carry scannability, which is what bolding a whole list of judgements duplicates. **This rule exists because it happened** — a briefing went to review with a bold phrase in nearly every paragraph, and the reviewer could not locate the argument.
- **In JA, counting expressions use Arabic numerals, not kanji numerals.** 1週間に4件, 4つの点, 損失は1日, 事故記録に1行, and numbered headings as `1.` rather than `一.`. Idiomatic adverbs keep their kanji form (一度も, 一つひとつ) — the rule is about counts, not about every occurrence of a number word.

## Gates (Must Pass Before Review)

1. **Anonymisation — binding.** Run the [anonymisation](../anonymisation/SKILL.md) skill over the full draft (EN, JA, and the social derivative if one is in scope) before anything moves toward a public surface. Its decision procedure applies paragraph by paragraph; if an example cannot be scrubbed, drop it for an industry baseline. **Fast pass:** if no paragraph draws on real client or engagement experience (e.g. the artefact is the organisation's own public code), the gate passes — note "anonymisation: no engagement material" in the handover and move on.
2. **Image references.** Every inline image `![...](path)` in both posts must resolve to a real committed file (e.g. `/blog/foo.png` → `site/public/blog/foo.png`). Grep and verify each one; missing assets block review — request them, do not ship without. A social derivative is exempt (it is not committed; any image is attached at publish time).
3. **Frame integrity.** Every H2 (and a deep dive's title) carries its tagline. Skimming headings alone must convey the argument.
4. **The preview actually contains the post.** Once the pull request has a deploy preview, fetch it and confirm **each language's blog index lists the post and each post URL returns 200**. Do this before requesting review, and do it against the preview rather than a local build — a local build passing proves the post compiles, not that the deployed site shows it. This gate is cheap and catches the whole class where the site builds successfully *without* your post: a draft flag, a locale or slug mismatch, a collection filter, a routing rule. **A green build is not evidence the post is there.** If the preview does not appear at all, say so rather than assuming it will; do not treat a missing deploy-preview check as proof that no preview was built.

   **Before concluding the post is missing, prove you are fetching the right host.** A wrong preview hostname 404s on *every* path, which is indistinguishable from a build that dropped your post — and the failure mode is mundane: Cloudflare truncates a branch alias at **28 characters**, so `content/calibration-deep-dive` (29) serves from `content-calibration-deep-div`, not the name you would construct. **This rule exists because it happened**, and the first reading was "the post is not in the preview". The check that separates the two cases costs one request: fetch the **blog index** as well as the post. Index 404 too → wrong host. Index 200 and post 404 → genuinely missing, which is the case this gate is for. Confirm the language prefix from the site's own route structure rather than assuming (`/en/blog/…`, not `/blog/…`) — that error 404s identically.

## Outputs

| Artefact | Destination |
|----------|-------------|
| EN post draft | `site/src/content/blog/en/<slug>.md` |
| JA post draft | `site/src/content/blog/ja/<slug>.md` |
| Social derivative (text + optional simple image) | **Only when the overlay scopes derivatives in for this artefact class.** Delivered to the publisher in-conversation; not committed to the repo |

A derivative is a compression of the post, not a teaser: lead with the strongest judgement, one supporting point, and a link to the post. It passes the same anonymisation gate. It may carry **one simple image** — a single bold visual with few, large labels (the post's diagram simplified often works). Never a dense graphic with many small-font labels; on a feed it renders unreadable. The image is delivered alongside the text for attachment at publish time, not committed.

## Review Gate: The PR Is the Human in the Loop

Drafts reach the sign-off owner as a **pull request** — never a direct commit to the publishing branch. The PR is the structural review gate: the sign-off owner reads the rendered drafts, edits or requests changes, and the merge is the publish decision. The skill's own gates (below) are what a draft must pass before that review is requested; they do not replace the human review, they make it worth the reviewer's time. Gates 1–3 run before the PR is opened. **Gate 4 necessarily runs after**, because it checks the deploy preview the PR itself produces — which is the point: the reviewer is being asked to read a rendered page, so something must confirm the page renders.

## Procedure

1. Ingest the artefact; extract the finding, the evidence, and who it serves.
2. Ingest the content requirement (Inputs above); if none has been stated, request it from the sign-off owner and stop until it arrives. The requirement's discussion point and perspective govern every drafting choice that follows.
3. Choose the frame (table above); record the choice and the reason in the handover notes that accompany the draft (for this repo: the Work Item report).
4. Draft the EN post in the chosen frame, following the editorial conventions and answering the requirement's discussion point for its stated audience; write each section's tagline after drafting the section (it is the conclusion, not the topic). Add a diagram or image where it clarifies (conventions above).
5. Run gate 1 (anonymisation) on the EN draft; rewrite or drop failing paragraphs.
6. Write the JA post as a native rewrite of the gated EN draft.
7. If — and only if — the overlay scopes a derivative in for this artefact class, write it from the gated post, with an optional simple image. Where it does not, say so in the handover and skip to the next step; offering the derivative anyway invites back the work the overlay just ruled out.
8. Run gates 1–3 end to end; fix or escalate anything failing.
9. Open (or update) the PR — the human-in-the-loop review gate.
10. Run gate 4 against the PR's deploy preview, and **put the per-language preview URLs in the handover** so the sign-off owner reads the rendered post rather than the diff. Only then request review. Publishing is the sign-off owner's merge decision, outside this skill.
