---
title: "The Controls That Report Success and Do Nothing"
description: "As PMOs push reporting, compliance checks and risk assessment onto AI, the failure that should worry you is not the control that breaks loudly. It is the one that returns a clean result while doing nothing at all — and we found four of them in our own delivery in a single week."
pubDate: 2026-07-31
tags: ["pmo", "governance", "assurance", "ai-agents", "devsecops"]
contentType: "briefing"
---

The House of PMO's trends for 2026 give PMOs a piece of advice worth taking seriously: *"Never trust a single data source. A truly data-driven PMO triangulates information from multiple systems."* It is sound. This briefing is about the failure it does not catch — the case where every source agrees, every check is green, and none of them looked at anything. We found four instances in our own delivery in one week, and we build this kind of tooling for a living.

## Key Judgements: The Control That Worries You Should Be the Quiet One, Not the Broken One

- **A control that fails loudly is cheap.** It interrupts someone, gets fixed, and costs an afternoon. A control that reports success while doing nothing costs whatever you built on top of the assurance, for as long as you believed it.
- **Triangulation is necessary and not sufficient.** Multiple sources protect you from one system being wrong. They do not protect you from every system being silent for the same reason — a check that never ran returns "nothing found" in exactly the format that "all clear" uses.
- **This class of failure scales with automation, which is what makes it a 2026 problem.** Every routine assurance you hand to an AI agent — report generation, compliance checks, risk flags — is another control whose inertness nobody will notice, because nobody is sitting behind it any more.
- **AI is specifically poor at catching it.** An automated loop optimises for the check being green. "Green" and "never ran" are indistinguishable to it unless you deliberately make them different.
- **The remedy is not more controls.** It is requiring each existing control to prove it executed, and defaulting an absent answer to *unknown* rather than *clean*.

## Situation: PMOs Are Being Asked to Govern AI-Assisted Delivery Just as Governance Is Being Deliberately Lightened

Two things are happening to PMOs at once, and they interact badly.

The first is AI adoption, now well past apprehension. The House of PMO describes a community "taking a sensible, pilot-based approach" — automating reporting, using the AI features already built into existing tools, applying generative AI to analysis. This is the right posture, and the same source is careful about the condition attached to it: *"AI doesn't replace PMO judgement. It amplifies it but only if the data underneath is sound and the questions being asked actually matter."*

The second is that governance is being right-sized rather than standardised: shorter reports, clearer dashboards, lighter templates, control levels matched to complexity. Also right, and overdue.

Put them together and you get a specific exposure. You have fewer people looking at each control, more controls running automatically, and a deliberate policy of not over-inspecting. That is a good operating model — provided the controls are actually running. Nothing in the model tells you when one stops.

The uncomfortable part is that a control which has quietly stopped working looks *identical* to a control that is working and finding nothing. In a well-run portfolio, most controls find nothing most of the time. Silence is the expected output.

## Analysis: Four Instances in One Week, in an Organisation That Builds Assurance Tooling

We are our own first client, so our evidence is our own delivery. In a single week, four separate controls reported success while doing nothing. None of them raised an alarm. Each was found by accident, or by someone deciding to test the mechanism rather than read its output.

**A security setting that accepted the change and discarded it.** We asked our code platform to enable two additional secret-scanning options. The request returned success. The settings stayed off. We repeated it on a second day, in a single call, and read the response body rather than the status code: success again, both still disabled. Anyone checking the status code — which is what a script does — would have recorded the control as enabled and moved on. It is now documented as a platform limitation with a manual workaround, but for a period we believed we had a control we did not have.

**A vulnerability feed reporting zero, where zero meant nothing.** We turned on automated dependency-vulnerability alerting and it reported no issues. That reads as health. It was not: the feed had never analysed the relevant part of the codebase, because analysis is triggered by a change to the main branch and none had happened. The next change landed and the count went from zero to three in about a minute. **A just-enabled feed reads a clean zero until something makes it run** — and that zero is indistinguishable from a genuine all-clear.

**Every automated gate green, on software that could not start.** Nine required automated checks passed on our published package. The package itself, installed the way a customer installs it, failed immediately — a dependency had removed a component we relied on, and our version constraint was open-ended. Our checks were green because a lockfile pinned a working version internally. **The gates proved the repository worked. Nobody was testing what a customer actually receives.** We have since added a check that installs the built artefact from scratch and exercises it, which is the control whose absence let the broken version ship.

**A verification step that certified a folder that did not exist.** During this week's work, a script verified that a set of files had copied correctly and that none contained sensitive strings. It reported a clean pass on both counts. It had been pointed at a path that did not exist, because an environment variable resolved differently between two steps. A missing target produced the same output as a clean result. Re-run against the correct path, it did genuinely pass — but the first report certified nothing while stating it had certified everything.

One more, from the same period, because it is the version most PMOs will recognise: our estimation records have fields for optimistic, likely and pessimistic effort, feeding a calculated forecast. Several records were saved with those fields empty. Nothing failed. The save succeeded, the record looked complete, the narrative notes read well. The only visible symptom was a blank column in a downstream calculation that nobody was looking at. **The data was not wrong. It was absent, and absence rendered as a well-formed record.**

## Evaluation: The Common Shape Is That Absence Is Rendered as Success

Five incidents, one structure. In every case the mechanism returned the same output for *"I checked and found nothing"* and for *"I did not check."* No system was lying. Each was accurately reporting an empty result, and an empty result is genuinely ambiguous.

That ambiguity is where the cost sits, and it has three properties worth understanding at board level.

**It is silent by construction, so it does not appear in incident data.** You will not find these in a risk register, because nothing was ever raised. They surface when someone independently discovers the underlying problem — a customer reporting broken software, an auditor asking for evidence — at which point the cost includes every decision made on the false assurance.

**It gets worse under exactly the conditions we are all moving toward.** More automation, fewer humans per control, deliberately lighter oversight. Each of those is defensible. Together they remove the accidental detection that used to catch this: someone who *expected* to see something, didn't, and asked why.

**Generative AI makes it more likely rather than less.** This is the part most relevant to PMOs adopting AI for compliance checks and reporting. An AI agent asked to make a check pass will reliably find the cheapest route to green, and "the check did not run" is the cheapest route of all. It does not require dishonesty — the agent has no way to distinguish an empty result from a skipped one either, and it will report the clean result in good faith and with confidence. Confident, well-formatted and empty is the characteristic output.

This is precisely the condition the House of PMO attaches to AI amplifying judgement: *only if the data underneath is sound*. An inert control does not produce unsound data. It produces no data, formatted as sound data — which is harder to catch, because every downstream quality check on the *content* will pass.

Triangulation helps against a wrong source. It does not help here, because the failure is not disagreement between sources. It is agreement between sources that are all quiet.

## Recommendation: Ask Each Assurance to Prove It Ran, and Make Absence Loud

Five questions, in the order we would ask them. None requires new tooling and none requires understanding how the controls are built.

1. **"When did this control last say no?"** Ask it of every automated assurance you rely on. A control that has never produced a negative result in its lifetime is not necessarily broken — but it is unevidenced, and it should be treated as unevidenced until someone demonstrates it can fail. This single question would have caught three of our five.

2. **"Show me evidence it executed, not evidence it is configured."** Configuration is what the setting screen shows. Execution is a timestamp, a record count, a log line. The gap between the two is where all five of ours lived. Where a control cannot show you it ran, that is your answer.

3. **"Are we testing what we build, or what the customer receives?"** These are different artefacts and the difference is where our most expensive instance sat. Whatever your equivalent is — the report the sponsor actually opens, the dashboard the executive actually sees, the deliverable the client actually installs — test that one.

4. **"Does an empty result read as clean, or as unknown?"** This is the cheapest structural fix available. A dashboard tile showing zero findings should be visibly different from one that has no data. Most tools will not do this by default. Asking for it is a small change with a disproportionate return.

5. **"What did we remove when we right-sized governance?"** Lightening governance is correct. The trap is lightening the *attention* while leaving the control in place, which produces exactly the inert-but-present state described here. Removing a control honestly is safer than keeping one nobody exercises: at least everyone knows where they stand.

For PMOs specifically, add one to the AI pilot checklist: **for every routine assurance you automate, define in advance what a genuine negative looks like, and confirm you have seen one.** If a newly automated compliance check has never flagged anything, you have not yet learned whether it works. You have learned that it is quiet.

We found four of these in a week while building tooling whose entire purpose is to catch them. That is not a claim about our competence either way. It is the point: this class of failure is not caught by caring about it. It is caught by mechanisms that make absence impossible to mistake for success.

---

*Sources: [House of PMO, "PMO Trends for 2026"](https://houseofpmo.com/blog/2026/01/05/pmo-trends-for-2026-house-of-pmo/). The incidents described are from our own delivery on the open-source [logic](https://github.com/lemur47/logic) repository, and are documented in its public commit history.*
