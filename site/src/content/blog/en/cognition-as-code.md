---
title: "Cognition as Code: Co-Evolving with AI Agents"
description: "Most organisations add AI to linear processes. A different approach: co-evolve with AI through a crystallisation cycle that turns tacit expertise into executable code. The moat isn't the code — it's the process that produces it."
pubDate: 2026-03-25
tags: ["cognition-as-code", "nfd", "bayesian", "pmo", "ai-agents", "conways-law"]
---

"We know AI is coming, but we don't know how to use it."

This sentence, in various forms, appeared at the [2026 Blue Light PMO Summit](https://houseofpmo.com/blue-light-report/) across emergency services, government, and infrastructure organisations. Hundreds of PMO professionals in the room. The consensus: AI will transform project management. The gap: nobody has a working model for *how*.

The dominant approach is what we'd call Layer 1 adoption: use an LLM as a text processing tool. Draft risk registers. Summarise meeting notes. Generate status reports. The House of PMO's 2026 AI course teaches exactly this — prompt engineering with ChatGPT, Copilot, and Gemini. It's useful. It's also a ceiling.

![Four-layer AI adoption stack — most PMO AI sits at Layer 1 (text tool), while pmo.run operates at Layers 2-4](/blog/cognition-as-code/four_layer_positioning.svg)

Layer 1 adoption treats AI as a faster typist. The PMO's processes don't change. The team structure doesn't change. The estimation methodology doesn't change. AI accelerates existing workflows without transforming them. And because the LLM is stateless — it doesn't learn from your project history, doesn't accumulate domain knowledge, doesn't get sharper over time — the productivity gain is bounded.

This post describes a different architecture. One where the AI system and the human team co-evolve, each making the other more capable in a compounding cycle. We call it *cognition as code*.

## Conway's Law for AI

In 1968, Melvin Conway observed that organisations design systems that mirror their communication structures. A company with four teams produces a four-module architecture. This isn't a suggestion — it's a law. The org chart becomes the system diagram.

The same law applies to AI adoption. A linear organisation — where knowledge flows through hierarchies, decisions are made in sequence, and expertise is siloed — will produce a linear AI architecture. The AI sits at the end of a pipeline: human decides, AI formats. This is Layer 1.

A co-evolutionary team structure produces something different. When the human expert and the AI system are in continuous dialogue — each informing the other, each reshaping the other's capabilities — the architecture that emerges is non-linear. Knowledge spirals rather than stacks.

Our own team structure is a deliberate Conway's Law choice. A CEO with 13 years of PMO field experience works in strategic dialogue with an AI CTO (Claude in claude.ai). The CTO's architectural decisions are implemented by a Claude Code agent team in a sandboxed environment. The CEO's tacit expertise becomes the CTO's crystallised knowledge, which becomes the agent's executable capability. The system produces spiral growth because the team *is* a spiral.

This isn't metaphor. It's architecture.

## Three Paradigms of AI Development

A 2026 preprint by Zhang identifies three paradigms for building AI agents, each reflecting a different assumption about where knowledge lives:

**Code-first.** Knowledge is encoded as deterministic logic. Decision trees, rule engines, mathematical models. Strengths: auditable, reproducible, precise. Weakness: can't handle ambiguity, can't learn from unstructured experience, brittle to novel situations.

**Prompt-first.** Knowledge is encoded as static system prompts. The LLM is given a persona and instructions, then responds to queries. Strengths: flexible, handles natural language, quick to deploy. Weakness: stateless — the system doesn't accumulate knowledge across sessions. Each conversation starts from zero. The prompt is a ceiling, not a foundation.

**Nurture-first.** Knowledge emerges through structured conversational interaction between a human expert and an AI system. The agent starts with minimal scaffolding and progressively grows through what the paper calls a "Knowledge Crystallisation Cycle." Strengths: compounds knowledge, produces transferable artefacts, scales the expert's cognition beyond their individual bandwidth. Weakness: requires a human expert willing to invest in the crystallisation process.

The paper maps this to a three-layer cognitive architecture, ordered by how frequently each layer changes:

- **Constitutional layer** (low volatility): core identity, values, architectural decisions. Changes rarely.
- **Skill layer** (medium volatility): crystallised domain knowledge. Changes when expertise deepens.
- **Experiential layer** (high volatility): conversation history, operational context. Changes constantly.

What makes this framework useful is the crystallisation cycle itself: field observation → prototype → formalised artefact → operational deployment → new observation. Each cycle doesn't just add a layer — it reshapes the layers beneath it.

## What Crystallisation Looks Like in Practice

Theory needs a worked example. Here's ours.

In January 2026, we built a Total Cost of Ownership calculator. A standalone Python script, 200 lines. It turned a common PMO question — "which option is actually cheaper over five years?" — into executable maths. TCO became our first FastAPI module with CRUD, tests, and an API.

In February, we built PERT estimation. Three-point estimation is textbook, but our version added "insight tags" — field-calibrated multipliers that adjust the pessimistic estimate based on real-world patterns (fragmented communication, multiple stakeholders, hidden dependencies). The tags encode consulting experience as composable parameters.

The PERT module didn't just add to TCO. It revealed a pattern: every module has a `core.py` (pure maths, MIT-licensed), a `router.py` (FastAPI endpoints), a `schemas.py` (validation), and a `crud.py` (persistence). This pattern — extracted later into `app/common/` — became the architectural DNA for every subsequent module.

In the same month, we built EVM (Earned Value Management). EVM depends on PERT: the duration estimates become the baseline's planned values. The module family chain — PERT feeds baselines, baselines feed EVM metrics — was the first sign that modules don't just coexist, they compound.

Then came Skills. We wrote the PERT, EVM, and TCO logic as markdown instructions — "Skills" — that Claude can execute conversationally, without deployment. Same maths, different runtime. A Claude Project with a PERT Skill produces the same numbers as the FastAPI endpoint. The crystallisation here: tacit PMO expertise (when to apply tags, how to read EVM signals, what TCO inputs to question) became transferable artefacts that any Claude instance can use.

In March, we built the Bayesian estimation calibration module. This one is the sharpest example of the crystallisation cycle. The research question — "can AI learn from estimation errors?" — led to a Nature Communications paper showing that LLMs plateau after a single observation when doing sequential belief updating. The answer: deterministic Bayesian maths, not LLM reasoning. The module uses conjugate normal-normal updating to learn systematic estimation bias from completed tasks.

But here's the spiral: the Bayesian module consumed PERT outputs (estimated durations) and produced calibration coefficients that reshape future PERT estimates. It didn't add to the stack — it fed back into it. And the shared CRUD patterns we extracted in the refactoring sprint meant the Bayesian module inherited clean infrastructure instead of copying boilerplate from three siblings.

Four modules. Three months. Each one reshaped the ones before it. That's not linear maturity — it's spiral growth.

![Knowledge crystallisation cycle — field observation flows through PoC, FastAPI, Skill/blog, and community signal, then back to observation](/blog/cognition-as-code/knowledge_crystallisation_cycle.svg)

## The Two-Tier Proof

The Bayesian module also demonstrated an architectural principle that appears independently in multiple research contexts: the separation of deterministic maths from LLM interpretation.

A 2026 Stanford working paper simulated FOMC monetary policy decisions using a dual-track framework. Track 1: Monte Carlo simulation with conjugate normal-normal Bayesian updating — the same formulas our module uses. Track 2: LLM-based deliberation where AI agents debate policy in natural language. Both tracks start from identical priors. The difference between their outputs — the "deliberation wedge" — reveals behavioural friction that formal models miss.

The architecture is clear: maths at the core, LLM at the interpretation boundary. The LLM adds value by contextualising what the numbers mean — "this pattern suggests stakeholder misalignment, not technical complexity" — but the numbers themselves must come from deterministic logic.

This separation isn't a design preference. It's a necessity. LLMs cannot accumulate precision across sequential observations. They generate text that resembles Bayesian reasoning, but the actual mathematical precision accumulation doesn't happen inside a forward pass. For any system that needs to *learn* from data over time — estimation calibration, risk pattern detection, performance trending — the maths must be separate and exact.

## Why This Matters: Linear vs Non-Linear Growth

A 2026 study in the Business Process Management Journal documented how one European PMO evolved its mandate over 16 years, through five stages: IT support → governance → strategic integration → enterprise authority with AI → corporate maturity. Each stage adds a mandate layer. None removes one.

This is linear evolution. Stage 3 takes years to reach. Stage 4 — where the PMO leads AI adoption — requires decades of accumulated governance maturity. Most PMOs stall at Stage 2 or 3 because adding governance layers without automation creates bureaucratic overhead. More reporting, more meetings, more Excel spreadsheets, same headcount.

The crystallisation model compresses this timeline. Each module we build encodes a governance capability as executable code rather than as a process document. EVM metrics aren't computed by a PMO analyst in a spreadsheet — they're computed by an API that any system can call. Bayesian calibration isn't a "lessons learned" meeting that nobody attends — it's a module that learns automatically from every completed task.

The difference between linear maturity and spiral crystallisation:

- **Linear:** add a governance layer → hire someone to run it → wait for it to mature → add the next layer.
- **Spiral:** observe a field pattern → crystallise it as a PoC → integrate into the architecture → the architecture reshapes how you observe the next pattern.

In linear models, each layer is independent. In spiral models, each cycle reshapes all prior layers. Our refactoring sprint (extracting `app/common/`) was the system recognising its own duplication and self-correcting — a higher-order crystallisation that the linear model has no mechanism for.

## The Moat

Open-source maths builds trust. Anyone can audit our PERT formula, verify our Bayesian update, check our EVM calculations. The code is MIT-licensed.

Field-calibrated data — "auth tasks in SIer projects take 1.31x the PERT estimate" — makes the maths accurate for specific contexts. The calibration coefficients are proprietary.

But the real competitive advantage is neither the code nor the data. It's the crystallisation process itself — the methodology by which tacit PMO expertise becomes executable code through human-AI co-evolution. The process that turned a veteran PM's "auth always takes longer" into a Bayesian posterior with σ=0.061. The process that compressed 16 years of linear PMO evolution into four months of spiral growth.

The code is public. The calibration data is proprietary. The crystallisation process is the moat.

---

*The logic modules described in this post are open source at [github.com/lemur47/logic](https://github.com/lemur47/logic). The Nurture-First Development framework is from [Zhang (2026)](https://arxiv.org/abs/2603.10808). The PMO layered mandate model is from [Monteiro (2026)](https://www.emerald.com/bpmj/article-abstract/doi/10.1108/BPMJ-09-2025-1573/1340718/Opening-the-black-box-of-disaster-recovery-in-SMEs?redirectedFrom=fulltext), Business Process Management Journal. The dual-track Bayesian/LLM architecture is from [Kazinnik & Sinclair (2026)](https://digitaleconomy.stanford.edu/publication/fomc-in-silico-a-multi-agent-system-for-monetary-policy-decision-modeling/), Stanford Digital Economy Lab. The LLM belief updating limitation is from [Qiu et al. (2026)](https://www.nature.com/articles/s41467-025-67998-6), Nature Communications.*
