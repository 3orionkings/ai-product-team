# Roadmap slides, second half of 2026 — speaker-notes export

Document id: LS-SLIDES-03
Date: 2026-05-12
Status: not marked superseded; not marked current
Author role: product team
Format: speaker notes exported from a slide deck; slide titles are preserved, visuals are not

Synthetic material. This is an invented roadmap for a fictional product, written for a demonstration. It contains the deliberate conflict that the W02 fixture exists to test: it describes a sending model that the later policy (`02-support-policy.md`) does not permit.

---

## Slide 1 — Larkspur Support: where we are going in H2

Notes: Thank the audience. Frame the half as "less time per ticket, same quality". Three themes: faster search, Reply Assist, admin reporting. This deck is about the second theme.

## Slide 2 — The problem agents tell us about

Notes: Agents say most routine tickets are the same five questions. They know the answer; the time goes into finding the document and typing the reply. Quote the internal survey (synthetic): a majority of agents said they would hand routine tickets to a tool if they trusted it.

## Slide 3 — Introducing Reply Assist

Notes: Reply Assist reads the ticket, pulls the right knowledge document and writes the reply. Emphasize "writes the reply", not "helps you write". That is the difference from a template library.

## Slide 4 — How it works

Notes: Three steps on the slide.

1. Ticket arrives and is classified as routine or exception.
2. For routine tickets, Reply Assist retrieves the matching document and composes a reply.
3. **Reply Assist will send routine replies automatically.** Agents handle only exceptions and spot-check a sample of the automatic replies afterwards.

Say this slowly; it is the headline. Routine means the five recurring categories on the next slide.

## Slide 5 — What counts as routine

Notes: Password and sign-in resets, opening hours and availability, order or delivery status, pause and resume of a membership or subscription, and "where is my item" questions. These are the categories where the knowledge document answers the question fully and the reply does not need judgment.

## Slide 6 — Target outcome

Notes: Target for the half (synthetic): a large share of routine tickets closed without an agent touching them, and a visible reduction in time-to-first-reply. Do not commit to a number out loud; the slide shows a range.

## Slide 7 — Risks and dependencies

Notes: Be candid here.

- **Policy sign-off has not been obtained.** The current reply policy says agents send replies. Automatic sending needs the support operations lead to agree to a policy change. That conversation has not happened yet.
- Retrieval must stay inside the workspace. Any cross-workspace leak would be disqualifying.
- Quality of the automatic replies needs an evaluation method we do not have yet.
- Agents may distrust the feature if the first automatic replies are wrong.

## Slide 8 — Next steps

Notes: Build a drafting version first so agents can see the output. Use what we learn to make the case for automatic sending. Revisit with support operations in the summer.

---

## Export notes

- This export was produced for the planning archive. It has not been reviewed since the presentation date.
- Nothing in this file records whether the sending model on slide 4 was later approved, deferred or withdrawn. Slide 7 states that policy sign-off had not been obtained as of 2026-05-12. Slide 8 proposes building a drafting version first.
- Readers comparing this file with `02-support-policy.md` (2026-09-20) will find that the policy does not permit what slide 4 describes. The two documents conflict. This file does not say which should win; that is a decision for the people named in the policy's rule R7 and for the human owner of the case.
