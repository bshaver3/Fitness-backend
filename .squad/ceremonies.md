# Ceremonies

> Team meetings that happen before or after work. Each squad configures their own.

## Design Review

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | before |
| **Condition** | multi-agent task involving 2+ agents modifying shared systems |
| **Facilitator** | lead |
| **Participants** | all-relevant |
| **Time budget** | focused |
| **Enabled** | ✅ yes |

**Agenda:**
1. Review the task and requirements
2. Agree on interfaces and contracts between components
3. Identify risks and edge cases
4. Assign action items

---

## Retrospective

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | after |
| **Condition** | build failure, test failure, or reviewer rejection |
| **Facilitator** | lead |
| **Participants** | all-involved |
| **Time budget** | focused |
| **Enabled** | ✅ yes |

**Agenda:**
1. What happened? (facts only)
2. Root cause analysis
3. What should change?
4. Action items for next iteration


---

## Retrospective with Enforcement

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | weekly |
| **Condition** | No *retrospective* log in .squad/log/ within the last 7 days |
| **Facilitator** | lead |
| **Participants** | all |
| **Time budget** | focused |
| **Enabled** | yes |
| **Enforcement skill** | retro-enforcement |

**Agenda:**
1. What shipped this week? (closed issues, merged PRs)
2. What did not ship? (open issues, blockers)
3. Root cause on any failures
4. Action items -- each MUST become a GitHub Issue labeled retro-action

**Coordinator integration:**
At round start, call Test-RetroOverdue (see skill retro-enforcement). If overdue, run this ceremony before the work queue.

**Why GitHub Issues, not markdown:**
Production data: 0% completion across 6 retros using markdown checklists, 100% after switching to GitHub Issues.

---

## Contract Sync

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | before |
| **Condition** | task adds, changes or consumes an API endpoint or response shape |
| **Facilitator** | lead |
| **Participants** | all-relevant |
| **Time budget** | focused |
| **Enabled** | ✅ yes |

**Agenda:**
1. State the endpoint, request and response shape
2. Check it against `openapi.json` in the backend repo
3. If the contract must change, follow the `fe-be-contract` skill. Leads decide the shape; do not ask the owner and do not wait for a merge
4. Record the cross-squad issue link

---

## Pre-Mortem

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | before |
| **Condition** | start of a milestone, or any feature that shows calorie targets, workout suggestions or diet plans to a user |
| **Facilitator** | lead |
| **Participants** | Fact Checker (Devil's Advocate mode), Rai, all-relevant |
| **Time budget** | focused |
| **Enabled** | ✅ yes |

**Agenda:**
1. Fact Checker gives the strongest case against the plan
2. Rai checks health-advice safety: attainable targets, no medical claims, clear disclaimers
3. Fact Checker verifies every formula and constant has a source
4. Decide: proceed, change, or cut
