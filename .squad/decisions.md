# Squad Decisions

## Active Decisions

### 2026-11-14: Shared FitTrack decisions (copied from `fittrack-shared`)

Full text: `../.squad/decisions.md` in the parent folder (upstream `fittrack-shared`). Read it when
that folder exists. The rules below apply even when it does not (CI, cloud agents).

- **Goal:** FitTrack tracks workouts, calories and food intake, and suggests attainable workouts
  and diet plans from the user's goals and physique.
- **Two squads:** `fittrack-backend` owns `fitness-backend/`; `fittrack-frontend` owns
  `fitness-tracker/` and product scope. A squad never edits the other repo. Cross-repo work goes
  through `squad delegate <squad> "<request + acceptance criteria>"`.
- **Contract:** `openapi.json` in the backend repo is the single source of truth for the API.
  Follow the `fe-be-contract` skill (`.squad/skills/fe-be-contract/SKILL.md`). Additive changes
  by default; breaking changes need sign-off from both Leads.
- **Recommendation safety:** guidance, not medical advice; every formula has a verified source;
  conservative, attainable targets; rule-based before any ML or LLM.
- **Autonomous flow:** the owner gives a task once. Never ask the owner to approve a contract,
  design, plan or triage; Leads decide. The contract goes in the feature PR, not a separate PR,
  and the frontend builds against the backend feature branch without waiting for a merge.
  Watchers (`../bin/fittrack start`) pick up delegated issues, so squads trigger each other.
- **Issue state:** `status:blocked` = waiting on the other squad (comment names the issue; the
  squad that finishes that work removes the label). `status:on-hold` = PR open and reviewed,
  waiting for owner merge. Issues stay open until the PR merges through `Closes #N`. Do not
  close issues by hand or assign them to people.
- **Human gates:** the owner merges the finished PRs once per feature, and that is the only
  planned owner step; agents never run mutating AWS commands; user data is private per user.
- **Milestones:** M1 foundation, M2 food and calorie intake, M3 targets, M4 suggestions, M5 launch.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
