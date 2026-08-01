---
title: "What to Verify When the System Runs Itself"
description: "As more of delivery is handed to AI, what boards must govern shifts from the deliverable to the mechanism producing it. But mechanisms do not fail by stopping. They keep reporting success while doing nothing — we found four in our own delivery in a single week. Here are the four points worth verifying."
pubDate: 2026-08-01
tags: ["pmo", "governance", "assurance", "ai-agents", "operating-model"]
contentType: "briefing"
---

Describing how it secures its own development, Anthropic puts the change of the last few years in one line: **"The security engineer's job evolves from monitoring bugs to monitoring loops."** What you govern has moved from the deliverable to the mechanism that produces it.

The difficulty is that the mechanism has its own trapdoors. It does not necessarily fail by stopping. **It keeps reporting success while doing nothing at all.** We found four instances in our own delivery in a single week — in an organisation whose business is building assurance tooling.

This briefing addresses one question. When executives and business leaders work with a PMO to run an organisation and its products on the assumption that AI is doing the work, **what should they verify in a self-running mechanism?**

## Key Judgements: What You Govern Has Moved to the Mechanism, and a Mechanism That Cannot Prove It Ran Is Not a Control

- **The decision axis is not "should we doubt the AI's output" but "can we make the mechanism producing that output show evidence it ran".** Inspecting outputs is no longer where governance is decided.
- **The expensive control is not the broken one. It is the empty one that keeps reporting success.** A control that breaks loudly gets fixed and costs an afternoon. One that keeps returning green while inert takes down every decision built on top of it, and leaves not one line in your incident record.
- **"Configured" and "executed" are different things, and only the second is auditable.** What a board should ask for is not a screenshot of a settings page but a record of execution.
- **If the detection method is wrong, adding controls will not raise the detection rate.** What needs to increase is not the count but the validity of what is being watched.
- **None of this is peculiar to AI.** "Reports clean, work never done" recurred throughout offshore development and multi-vendor governance, and it is continuous with the deference PMOs already know from estimates, risk analysis and completion reports. Returning to fundamentals gets you there faster than chasing the trend.
- **Better prompting will not reach it.** Instructions are not reproduced, not audited, and not carried into the next conversation. A control has to be built into the environment and the structure.

## Situation: Under AI-Assisted Delivery the Number of Controls Does Not Fall — What Falls Is the Number of People Watching Them

Two things are happening at once, and the combination is what bites.

The first is that AI implementation has moved on. Report generation, assurance reviews, risk analysis — the PMO's routine work is being automated in turn. The second is that governance itself is deliberately being lightened: shorter reports, thinner templates, control levels matched to complexity. Both are right, and both were overdue.

Put them together and a specific exposure appears. **Fewer people are watching each control, more controls run automatically, and not looking too closely is a deliberate policy.** That is a sound operating model — provided the controls are actually running. Nothing in the model tells you when one stops.

And a control that has quietly stopped is **indistinguishable** from one that is running and finding nothing. In a well-run organisation, most controls find nothing most of the time. Silence is the expected output.

Layered on top of this is a question about the PMO's own equipment. Look at the standard training: House of PMO's "Practical AI Skills for the PMO" lists access to Microsoft Copilot, ChatGPT or Google Gemini among its technical requirements, and covers governance and assurance reviews alongside prompt packs. The course is explicit that it "focuses on augmentation rather than automation", and within that scope it is right. **The problem lies past the point where augmentation ends.** The moment your delivery moves to mechanisms that run without anyone instructing them, the premise of governing from a browser chat window stops reaching. Verifying a mechanism means getting inside it.

One caution while doing so: do not be moved by the marketing. There will always be a next line — loops are old, graphs are next. What deserves monitoring is not the **name** of the pattern but the pattern **itself**: agent loops, permission separation, single-purpose identity, dashboards.

## Analysis: A Self-Running Mechanism Does Not Break by Stopping — It Breaks While Continuing to Report Success

We are our own first client, so the evidence is our own delivery. Four points to verify, each paired with something that actually happened.

### 1. Can You Make the Control Show Evidence That It Executed?

That a setting is correct and that a control is running are two different claims.

We asked our development platform to enable additional secret-detection settings. **The request returned success. The settings stayed off.** We repeated it on another day as a single call and read the response body rather than the status code, which is how we found out. Anyone reading only the status code — which is exactly what a script reads — records the control as enabled and moves on.

There was a second of the same kind: an installation procedure wrote its configuration correctly, and that very configuration caused none of the checks to load at all. **The installer reported success throughout.** An AI implementing a check, never enabling it, and then reporting "the checks are working fine" is the same shape of failure.

### 2. Can You Separate "Nothing Found" From "Never Looked"?

We enabled dependency-vulnerability alerting and it reported zero findings. That reads as health. It was not. **The feed had never analysed the target at all.** Analysis is triggered by a particular event, and that event had not yet occurred. When the next change landed, zero became three in about a minute. A zero from a newly enabled feed wears the same face as a harmless one.

In the same week, a procedure verifying that a set of files had copied correctly reported a clean pass on both of its checks. **It had been verifying a location that did not exist**, because an environment variable resolved to different values in two steps. An absent target produced the same output as a clean result. Re-run against the right path it genuinely passed — but the first report certified nothing while stating it had certified everything.

### 3. Can the Detection Method Itself Catch the Failure You Have in Mind?

This is the most expensive question, because it is about a control's field of view rather than the number of controls.

In our public repository an identifier appeared on a surface it was not intended for. Chasing the cause, we inspected the configuration files and confirmed every one of them was correct. **But the operation had bypassed configuration entirely, passing the value inline.** A check that reads configuration therefore cannot detect this failure, whatever has happened. The check returned clean, the clean result was accurate, and it still did not answer the question. **Not "we looked and found nothing", but "the answer was never in the place we looked".**

A costlier example of the same shape: nine required automated checks were green on a product we published. Installed the way a customer installs it, that product failed to start immediately. **The checks were verifying what we had built. Nobody was verifying what the customer receives.** We have since added a check that installs the artefact from scratch and actually starts it — the control whose absence let a broken release ship.

### 4. Is the Control Still Alive After Repeated Change?

Controls that worked at the outset die quietly as changes accumulate, and their death is undetectable until somebody actually rings the bell. An organisation with no periodic exercise of its controls is leaving their liveness to chance.

## Evaluation: This Is Not an AI Problem — It Is a Structure We Already Know From Offshore Delivery and From Deference in the PMO

It is better not to be distracted by the novelty. **"Reports clean, work never done" recurred throughout offshore development and multi-vendor governance.** A distant executor, an actuality that is awkward to check, a well-presented report — once those conditions hold, whether the executor is a person or a model is not the essential part.

In a PMO the pattern is more familiar still. Cases where **deference contaminates the material for a decision** — estimates, risk analysis, completion reports — and makes the situation worse have been observed over and over. It is not dishonesty. Output that matches expectations is simply likelier to be chosen.

AI does this without any dishonesty at all. **Having no means of distinguishing an empty result from a skipped one, it reports in good faith, with confidence, in a well-formed shape.** Confident, well-presented and hollow is the characteristic output. Every downstream quality check on the content then passes, because there is no content to fail.

So chasing the trend breaks down. **Bringing across what offshore and multi-vendor governance already taught us, and returning to fundamentals, gets to genuine mechanism verification faster.** What we have always demanded of a remote executor — evidence of execution, sampling, a real example of a negative result — carries over to AI agents unchanged.

## Recommendation: Build Controls Into the Environment and the Structure Rather Than Into Prompts, and Make Absence Loud

The transition we went through ourselves is worth stating first. **We began by trying to raise quality through better instructions. It did not reach.** Instructions are not reproduced, not audited, and not carried into the next conversation. A good instruction produces a good single run; it does not produce a control. So we moved the work from the layer of instructions to the layer of environment and structure — the environment executes the checks, the structure separates the permissions, and the record exists without anyone writing it. **A prompt pack is not a control.** That is our own correction, and it is also the ordering to build into an AI adoption plan.

Five questions a board and a PMO can use tomorrow. None needs new tooling or any understanding of how the controls are built.

1. **"When did this control last say no?"** A control that has never produced a negative result in its life is not necessarily broken, but it is **unevidenced**. Treat it as unevidenced until it is demonstrated. This one question would have caught three of our five.
2. **"Show me evidence it executed, not evidence it is configured."** Configuration is what the settings page shows. Execution is a timestamp, a count, a log line. All five of ours lived in the gap between the two. Where a control cannot show you it ran, that is your answer.
3. **"Are we verifying what we built, or what the customer receives?"** They are different artefacts. The report the sponsor actually opens, the dashboard the executive actually sees, the deliverable the client actually installs — verify that one.
4. **"Does an empty result read as clean, or as unknown?"** The cheapest structural fix available. A display of zero findings should look different from a display with no data. Almost no tool does this by default. Asking is enough.
5. **"What did we remove when we right-sized governance?"** Lightening governance is correct. The trap is **leaving the control in place and removing only the attention**, which is precisely the present-but-inert state described here. Retiring a control honestly is safer than keeping one nobody exercises: at least everyone knows where they stand.

Add one line to the PMO's AI adoption plan: **for every control you automate, define in advance what a genuine negative looks like, and see one at least once.** If a newly automated control has flagged nothing yet, you have not learned whether it works. You have learned that it is quiet.

Finally, the unsolved part. **An operation that bypasses configuration is invisible to every check we currently have.** Not to the ones that read file contents, not to the ones that read recorded text, not to the ones that read the artefact. Catching it mechanically would need something that watches a different target at the moment of transmission. Whether that is worth building, we have not yet decided. **This class of failure is not caught by caring about it. It is caught only by mechanisms that make absence impossible to mistake for success.**

---

*Sources: [Anthropic, "How Anthropic secures its AI-native software development lifecycle"](https://claude.com/blog/how-anthropic-secures-its-ai-native-software-development-lifecycle); [House of PMO, "Practical AI Skills for the PMO" course outline (v2.0)](https://training.houseofpmo.com/wp-content/uploads/2026/03/Practical-AI-Skills-for-the-PMO-Course-Outline-and-Technical-Requirements-v2.0.pdf). Every incident described happened in the development of our own public [logic](https://github.com/lemur47/logic) repository and is recorded in its history.*
