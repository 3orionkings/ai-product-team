# Sample tickets and knowledge-document indexes

Document id: LS-TIX-05
Date: 2026-09-15
Status: current
Author role: support operations

Synthetic material. Every ticket below was written for this demonstration. No ticket is derived from a real message. Requester identity is deliberately absent: the fields that would hold a name, address or account number are omitted by construction, not redacted after the fact.

## Workspaces

| Workspace id | Synthetic customer | Document id prefix |
|---|---|---|
| `ws-alpha` | A community bicycle-rental service | `A-` |
| `ws-beta` | A houseplant subscription service | `B-` |

## Knowledge-document index — ws-alpha

| Id | Title | Tags | Summary |
|---|---|---|---|
| A-KB-01 | Station pickup schedule | schedule, station, hours | When bicycles can be collected from each station and how the schedule changes on public holidays. |
| A-KB-02 | Lost key fob procedure | fob, lost, access | What a member does when a key fob is lost and how a replacement is issued. |
| A-KB-03 | Membership pause and resume | pause, resume, membership | How to pause a membership for up to two months and how to resume it. |
| A-KB-04 | Helmet policy | helmet, safety | Whether helmets are provided at stations and the rules for using one's own. |

## Knowledge-document index — ws-beta

| Id | Title | Tags | Summary |
|---|---|---|---|
| B-KB-01 | Watering schedule FAQ | schedule, watering, care | How often each plant in the subscription should be watered and how to adjust in winter. |
| B-KB-02 | Delivery window changes | delivery, window, reschedule | How to move a delivery to a different day or window. |
| B-KB-03 | Pot size guide | pot, size, repotting | Choosing a pot size when a plant outgrows its current one. |
| B-KB-04 | Pause subscription | pause, subscription | How to pause the subscription for one or more months. |

Note for readers of the corpus: the tag `schedule` appears in both workspaces (A-KB-01 and B-KB-01), and the word "pause" appears in a title in both workspaces (A-KB-03 and B-KB-04). These overlaps are intentional. They are the shapes under which a retrieval component that filters by workspace only on some paths would leak, and they are what the negative test in `07-cross-workspace-negative-test-2026-10.md` probes.

## Tickets — ws-alpha

### T-ALPHA-001

- Created: 2026-09-10 (synthetic)
- Category: schedule
- Subject: Can I pick up a bike before the station opens?
- Body: I have an early start on weekdays. Is there any way to collect a bicycle before the posted opening time, or is the schedule fixed?
- Expected relevant documents: A-KB-01

### T-ALPHA-002

- Created: 2026-09-10 (synthetic)
- Category: access
- Subject: Lost my fob over the weekend
- Body: My key fob is gone. How do I stop it being used and get a new one?
- Expected relevant documents: A-KB-02

### T-ALPHA-003

- Created: 2026-09-11 (synthetic)
- Category: membership
- Subject: Pausing while I am away
- Body: I will be away for six weeks. Can I pause my membership rather than cancel, and does the pause start immediately?
- Expected relevant documents: A-KB-03

### T-ALPHA-004

- Created: 2026-09-12 (synthetic)
- Category: safety
- Subject: Helmets at the riverside station
- Body: Are helmets available at the riverside station, or should I bring my own? Is there a size range?
- Expected relevant documents: A-KB-04

## Tickets — ws-beta

### T-BETA-001

- Created: 2026-09-10 (synthetic)
- Category: care
- Subject: How often to water the trailing plant
- Body: The care card says "moderate". What does the watering schedule look like in practice, and does it change now that it is getting colder?
- Expected relevant documents: B-KB-01

### T-BETA-002

- Created: 2026-09-11 (synthetic)
- Category: delivery
- Subject: Move next delivery to the weekend
- Body: Next month's delivery falls on a day I will not be home. Can I change the window?
- Expected relevant documents: B-KB-02

### T-BETA-003

- Created: 2026-09-12 (synthetic)
- Category: care
- Subject: Roots coming out of the pot
- Body: One plant has roots showing at the drainage hole. What size pot should I move it to?
- Expected relevant documents: B-KB-03

### T-BETA-004

- Created: 2026-09-13 (synthetic)
- Category: subscription
- Subject: Pause for the summer
- Body: I would like to pause the subscription for two months. Will my plan and pricing tier stay the same when I come back?
- Expected relevant documents: B-KB-04

## How these tickets are used

- In the W02 run, the tickets give the journey designer and the acceptance designer concrete entry points: a ticket arrives, Reply Assist retrieves from the ticket's own workspace, a labeled draft appears, the agent sends. Every ticket here is routine in the sense of `03-roadmap-slides-2026-05.md` slide 5, which is exactly why the drafts-only versus automatic-sending question matters for all of them.
- In the W10 run, T-ALPHA-001 and T-BETA-001 are the pair whose shared `schedule` tag is used by the negative test in document 07.
- No ticket body is to be quoted in a public report as if it came from a person. They are fixtures.
