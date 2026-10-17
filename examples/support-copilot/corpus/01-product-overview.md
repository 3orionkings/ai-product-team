# Larkspur Support — product overview and the proposed Reply Assist feature

Document id: LS-DOC-01
Date: 2026-09-08
Status: current
Author role: product owner
Audience: product, support operations, engineering

Synthetic material. Larkspur Support, Reply Assist, the workspaces and every figure in this document are invented for a demonstration and describe no real product.

## 1. What Larkspur Support is

Larkspur Support is a help-desk product. A customer organization that buys it gets a **workspace**. Inside a workspace, support **agents** (the customer's own staff) answer **tickets** raised by that customer's end users, and they maintain a small library of **knowledge documents**: how-to articles, policy notes and answer templates that agents consult while writing replies.

Workspaces are independent of one another. A workspace never sees another workspace's tickets or knowledge documents. Two synthetic workspaces are used throughout this corpus:

- `ws-alpha`: a community bicycle-rental service.
- `ws-beta`: a houseplant subscription service.

Their tickets and knowledge-document indexes are listed in `05-sample-tickets.md`.

## 2. Core concepts

| Term | Meaning in this corpus |
|---|---|
| Workspace | The isolation boundary. Every ticket, document, agent and draft belongs to exactly one workspace. |
| Ticket | A request from an end user, with a subject, a body and a category. In this corpus tickets carry no personal data. |
| Knowledge document | A short article owned by one workspace, identified by an id such as `A-KB-01`. |
| Agent | A human member of the workspace who reads tickets and sends replies. |
| Draft | Text proposed to an agent as a starting point. A draft is not a reply until an agent sends it. |
| Retrieval | Selecting knowledge documents relevant to a ticket or query. Retrieval is scoped to the requesting workspace; see `04-workspace-isolation-requirement.md`. |

## 3. How an agent answers a ticket today (without Reply Assist)

1. The agent opens a ticket in the workspace queue.
2. The agent searches the workspace's knowledge documents by title or keyword.
3. The agent writes a reply, possibly pasting from a template.
4. The agent clicks Send. The reply is recorded in the ticket's history with the agent's identity and a timestamp.

Step 2 and step 3 are where time is spent. Support operations reports (synthetic figure) that a typical agent handles routine tickets in several minutes and spends most of that time locating the right document and adapting its wording.

## 4. The proposed Reply Assist feature

Reply Assist adds one panel to the ticket view. When an agent opens a ticket:

1. Reply Assist retrieves up to five knowledge documents from the **agent's own workspace** that appear relevant to the ticket's subject and body.
2. Reply Assist produces a **draft reply** that cites which retrieved documents it drew on.
3. The draft appears in the panel with a visible label reading "Draft — not sent".
4. The agent reads the draft, edits it or discards it, and then sends the reply themselves using the existing Send control.

The agent remains the author of record of whatever is sent. Reply Assist has no Send control of its own and no scheduled or background path that produces an outbound message. This is a design choice of the feature and also the current rule of `02-support-policy.md`, which governs sending authority.

### 4.1 What Reply Assist does

- Retrieve workspace documents for the open ticket.
- Draft a reply grounded in those documents, with citations the agent can check.
- Offer the draft for editing.
- Record that a draft was shown, and whether the agent used, edited or discarded it.

### 4.2 What Reply Assist does not do

- It does not send. See `02-support-policy.md`.
- It does not retrieve across workspaces. See `04-workspace-isolation-requirement.md`, which is a protected requirement.
- It does not close tickets, change ticket status or write to the ticket history on its own.
- It does not learn from one workspace's documents to answer another workspace's tickets.

## 5. Retrieval behavior

Retrieval runs against a per-workspace index of knowledge documents. The index supports exact-title matching, keyword matching and, since release 0.9.0-rc1 (`06-changelog.md`), tag-based matching intended to improve recall for short queries. Every retrieval call carries the requesting workspace id. The requirement that results be limited to that workspace is WS-ISO-1 in document 04.

## 6. Relationship to earlier roadmap material

Roadmap slides presented in May 2026 (`03-roadmap-slides-2026-05.md`) described a broader ambition for Reply Assist, in which routine replies would go out without an agent touch. This document describes a drafting feature. Whether the May ambition is withdrawn, deferred or still intended for a later phase has not been recorded as a decision in any document available to this corpus. Readers should not infer one.

## 7. Open points for the feature proposal

- The sending model: drafting only (as here and in policy 02) versus the automatic sending described in the May slides. This is an authority question for the support operations lead and the product owner, not a design preference.
- Whether the draft label wording and position meet the accessibility expectations of the ticket view.
- Which ticket categories, if any, should have Reply Assist disabled by default.
- How the "draft shown / used / edited / discarded" record is surfaced to workspace administrators.
