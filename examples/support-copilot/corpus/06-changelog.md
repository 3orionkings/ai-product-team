# Larkspur Support — release notes

Document id: LS-CHG-06
Status: current; appended with each release
Author role: engineering

Synthetic material. These release notes describe a fictional product built for a demonstration. Version numbers and dates are invented and are used by other documents in this corpus to anchor which build a test ran against.

Format: newest first. Each entry lists what changed, what did not change and which requirement or policy an item relates to where that is known.

---

## 0.9.0-rc1 — 2026-10-08 (release candidate)

Changed

- Retrieval: added tag-based matching to the per-workspace knowledge index to improve recall for short queries of one or two words. Tags are the comma-separated values shown in each workspace's knowledge-document index.
- Retrieval: ranking now merges title matches, keyword matches and tag matches into one ordered result list before the result limit is applied.
- Reply Assist panel: citations in a draft now link to the retrieved document's title within the workspace.
- Administration: added a per-workspace report of drafts shown, used unchanged, edited and discarded (policy rule R6).

Not changed

- Reply Assist produces drafts only. The Send control belongs to the ticket view and to the agent.
- The draft label "Draft — not sent" is unchanged and remains non-configurable (policy rule R3).

Notes

- Release readiness review for 0.9.0 has been proposed and is pending. The isolation requirement WS-ISO-1 is listed as a readiness criterion. The most recent isolation test on record is RA-ISO-POS-01 against build 0.7.1.

## 0.8.1 — 2026-09-24

Changed

- Ticket view: the Send control is disabled until the agent has opened and scrolled a shown draft at least once (policy rule R4).
- Ticket view: removed the keyboard shortcut that previously allowed sending from the queue list without opening the ticket.

Not changed

- Retrieval paths and the workspace filter.

## 0.8.0 — 2026-09-10

Changed

- Reply Assist panel introduced behind a per-workspace feature flag, default off. When on, the panel retrieves up to five documents from the agent's workspace and shows a labeled draft.
- Drafts record the documents they cite.
- Added the "Draft — not sent" label to every piece of proposed text.

Not changed

- Who sends a reply: the agent, using the existing Send control.

Notes

- This release implements the drafting feature described in `01-product-overview.md`. It does not implement anything beyond drafting.

## 0.7.1 — 2026-08-20

Changed

- Added positive isolation test RA-ISO-POS-01 to the test suite. It exercises exact-title queries from ws-alpha and ws-beta and asserts that every result belongs to the requesting workspace. First run and pass recorded on 2026-08-19 (`04-workspace-isolation-requirement.md`).

Not changed

- Retrieval behavior.

## 0.7.0 — 2026-07-15

Changed

- Retrieval: introduced the per-workspace knowledge index. Every retrieval call carries a workspace id, and the title and keyword lookup paths filter on it. This is the first implementation of requirement WS-ISO-1 (approved 2026-07-02).
- Knowledge documents gained a tags field, populated but not yet used for matching.

Not changed

- Ticket view and sending.

## 0.6.0 — 2026-06-03

Changed

- Knowledge documents: agents can create, edit and archive documents within their workspace.
- Ticket view: added keyword search over the workspace's knowledge documents.

Not changed

- No assistance features exist in this release. Agents search and write replies themselves.

---

## Reading these notes alongside the other documents

- Nothing in 0.6.0 through 0.9.0-rc1 changes who sends a reply. Every entry that touches the ticket view either leaves sending with the agent or tightens the read-before-send rule. The roadmap slides of 2026-05-12 describe a sending model that no release implements.
- The retrieval component changed in 0.9.0-rc1 (tag matching, merged ranking). RA-ISO-POS-01 ran against 0.7.1. A test result from one build does not establish the behavior of a later build whose tested component changed; see `02_ARCHITECTURE.md` §11.5 in the package specification for the general rule, and `07-cross-workspace-negative-test-2026-10.md` for what was found when the release candidate was tested.
