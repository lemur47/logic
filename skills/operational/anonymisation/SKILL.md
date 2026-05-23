---
name: anonymisation
description: Binding rule for any content drawing on real client or engagement experience — blog posts, talks, marketing, public case studies. Triggers the moment material moves toward a public surface and references a client, vendor, project, team composition, sector, scale, or timeline.
---

# Anonymisation

Consulting and PMO content is credible because it draws on real experience. That experience is governed by NDAs and trust relationships. Breaking either costs you future clients, legal standing, and referrals. This skill is the binding rule for extracting **lessons** from real experience without exposing the **parties**.

If you cannot satisfy this rule, drop the example and use an industry baseline.

> **This skill is organisation-neutral.** The values specific to your organisation — who your core audience is, who owns confidentiality sign-off, which agreements bind you — live in a local overlay (`CALIBRATION.local.md`) kept out of version control, not in this file. Create your own from the template in this directory's README. The four-layer structure and decision procedure below are universal.
>
> **The examples below are illustrative and fictional.** They demonstrate the *failure modes*, not real engagements, and they name no real party. Keep it that way: when editing this skill, never replace a fictional example with a real case, even as a "bad" one. A document about anonymisation must itself be anonymised.

## The Four Layers

Each layer must be checked independently before publishing.

### Layer 1 — Identity (the NDA layer)

**Rule:** No reader should be able to deduce the client, vendor, sector + scale combination, or project from the content — alone or combined with other public information.

Failure modes:
- Direct names (a named client or a named consultancy).
- Sector + scale collocations ("the largest e-commerce company in [country]", "one of the top three banks in [country]").
- Vendor-type + engagement-type collocations ("a global consulting firm on an e-commerce marketing engagement").
- Project-shape signatures ("a 30-person team across AI vendor, SIer, and freelancers" narrows to a small set of identifiable engagements).
- Time markers that pin it down ("in our latest project…" + sector → triangulable).

### Layer 2 — Data (the numbers layer)

**Rule:** Prefer industry baselines. If real project data must be used, normalise it.

- **Industry baseline first.** "30% of infrastructure migration projects succeed" is a public figure. Use it as the anchor and frame the learning against it.
- **Normalise when real data is unavoidable.** Convert absolute values to ratios, percentages, multipliers, or order-of-magnitude buckets. "Success was 2.6× the industry baseline" beats "We delivered £4.2 m in savings."
- **Never publish raw counts, costs, durations, or headcounts from a real engagement.**

### Layer 3 — Narrative (the story layer)

**Rule:** The story around the numbers leaks too. Scrub the use case as carefully as the data.

- **Generalise the use case** to the *class* of engagement ("infrastructure migration with significant data dependency"), not the specific engagement.
- **Strip identifying role-and-vendor combinations.** "A telco client with two AI vendors and an offshore team" identifies fewer than five engagements globally.
- **Avoid time anchors.** "Recently", "last year", "in our current engagement" all pin the case down. Use "in our experience" or "in one engagement we observed".

### Layer 4 — Tone (the framing layer)

**Rule:** No pejorative framing of anonymised actors.

Calling an unnamed SIer "old-fashioned" reads as a complaint about an identifiable party even when no name is given. It also damages the audience relationship — the actors you anonymise are often part of your own audience (see your calibration overlay). Frame systemic issues as patterns ("traditional fragmented-reporting workflows remain common in mid-market SIers"), not as critiques of unnamed individuals.

## Decision Procedure

For every paragraph drawing on real experience, in order:

1. **Can I make this point with an industry baseline alone?** If yes, do that. Stop.
2. **If the real case is needed, can I fully strip Layer 1 (identity) without losing the point?** If no, drop the example.
3. **Are the numbers normalised per Layer 2?** If no, normalise or drop.
4. **Is the narrative scrubbed per Layer 3?** If no, rewrite the framing.
5. **Is the tone neutral per Layer 4?** If no, rewrite.
6. **Final filter:** read the paragraph back through the eyes of the *client in question*. Would they recognise their case and feel exposed? If yes, rewrite or drop.

## Bad Examples

*All fictional — illustrating the failure mode, naming no real party.*

**Bad 1 — Sector triangulation + vendor inference.**

> "At the largest e-commerce company in [country], we introduced a data-analytics AI for marketing analysis. As consultant and programme PMO on a global-consulting-firm engagement, we simulated 3–5 year sales forecasts from historical sales data."

Why bad: "the largest e-commerce company in [country]" resolves to a single named firm. "Global consulting firm" on that account narrows to two or three names. Both parties become identifiable, alone or combined with public information — NDA exposure, legal risk, loss of trust. The leak is the *collocation*, not any single phrase, and it happens in any language: the same sentence in translated marketing copy triangulates exactly the same way.

**Bad 2 — Project-shape signature.**

> "We help a consumer-finance company automate its call-centre operations using AI operators. The programme runs about 30 people across an AI vendor, a systems integrator, and freelancers."

Why bad: sector + size + team composition together form a signature that narrows to a small set of known engagements. Sharing any follow-on challenge would expose more. Loss of trust.

**Bad 3 — Pejorative framing of an unnamed party.**

> "A systems integrator ran the multi-vendor, multi-stakeholder setup with an outdated mindset from almost 20 years ago. They forced every stakeholder to write fragmented task reports and to sit through endless meetings."

Why bad: the underlying problem (fragmented reporting and meeting overload) is legitimate and the SIer audience would benefit from it being surfaced. But the framing reads as a complaint about a specific identifiable party, and the tone alienates the very readers the content is trying to reach. Contrast Good 2, which frames the same issue as a pattern.

## Good Examples

**Good 1 — Industry baseline + normalised learning.**

> "The industry baseline for infrastructure migration success sits at around 30%. In our experience that ratio rises to roughly 80% when the project treats data migration as a deliberate, calibrated risk during planning rather than an execution-phase problem."

Why good: public baseline anchors the claim. The learning is expressed as a ratio improvement, not absolute numbers. No client, no project, no time anchor. The point about calibrated PERT and planning lands clearly.

**Good 2 — Pattern across engagements.**

> "PMO work is not only about the current project or programme — it is also about organisational change management running alongside. Busy managers consistently lack the time to observe and contemplate the systemic problems shaping their delivery environment. The PMO can help by surfacing systemic feedback loops from observational data and offering scenario planning backed by Monte Carlo simulation."

Why good: real insight from real engagements, framed as a pattern across engagements rather than a single case. No identifying data, no actor critique, no time anchor.

## When to Apply

The skill triggers on any content moving toward a public surface:

- Blog posts (any language).
- Marketing material and landing-page copy.
- Talks, slides, conference submissions.
- Public case studies.
- Open-source repo READMEs and documentation that include illustrative examples.
- Any social-media post drawing on engagement experience.

The skill does not gate internal-only artefacts (operational trackers, sprint retros, internal docs). But internal material frequently gets extracted into public content later; applying the discipline at write time saves rework.

## Out of Scope for v0.1

- Quantitative anonymisation techniques (k-anonymity, differential privacy, etc.). These belong in the data-pipeline layer, not in editorial content.
- Legal review process. This skill is the editorial guardrail, not legal sign-off. Borderline cases escalate to the confidentiality sign-off owner named in your calibration overlay.
