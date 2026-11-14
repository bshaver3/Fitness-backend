# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| Architecture, data model, API contract change | Lead | New DynamoDB table, endpoint shape, splitting `main.py` |
| Issue triage and cross-squad requests | Lead | `squad` label inbox, `[cross-squad]` issues from frontend |
| API endpoints, models, persistence | Backend | Food log CRUD, calorie-intake totals, profile fields |
| Recommendation and target logic | Coach | TDEE and macro targets, workout suggestions, diet plan rules |
| Tests and quality | Tester | pytest suite, contract tests, bug reproduction |
| Auth, data access, hardening | Security | `auth.py`, per-user scoping, CORS, rate limits, dependency audit |
| CI, deploy config, release | DevOps | GitHub Actions, `Procfile`, Elastic Beanstalk runbook |
| Documentation | Docs | README, API reference, ADRs, changelog |

Add or edit rows here only when their agent names also exist in the casting registry.

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Lead |
| `squad:{name}` | Pick up issue and complete the work | Named member |

### How Issue Assignment Works

1. When a GitHub issue gets the `squad` label, the **Lead** triages it — analyzing content, assigning the right `squad:{member}` label, and commenting with triage notes.
2. When a `squad:{member}` label is applied, that member picks up the issue in their next session.
3. Members can reassign by removing their label and adding another member's label.
4. The `squad` label is the "inbox" — untriaged issues waiting for Lead review.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn the tester to write test cases from requirements simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. The Lead handles all `squad` (base label) triage.

## Cross-Squad Routing

| Situation | Action |
|-----------|--------|
| Work belongs to the frontend repo | Lead runs `squad delegate fittrack-frontend "<request + acceptance criteria>"`. Never edit `../fitness-tracker` from this squad. |
| Incoming `[cross-squad]` issue | Lead triages it like any `squad` issue and starts work at once. No owner approval. |
| Your work unblocks an issue in `bshaver3/fitness-tracker` | Comment there with branch name and summary, then `gh issue edit <n> --repo bshaver3/fitness-tracker --remove-label status:blocked`. |
| Work finished, PR open and reviewed | PR body has `Closes #N`. Label the issue `status:on-hold`. Do not close it. |
| API contract change | Follow the `fe-be-contract` skill (`.squad/skills/fe-be-contract/SKILL.md`). |
| Quick question about the other repo | Read `../fitness-tracker` (read-only), or ask through `copilot -C ../fitness-tracker --agent squad -p "<question>"`. |
