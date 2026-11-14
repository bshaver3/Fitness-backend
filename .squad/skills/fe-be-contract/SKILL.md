---
name: "fe-be-contract"
description: "How the FitTrack backend and frontend squads agree, change and consume the API contract without waiting for the owner, so the two repos never drift apart."
domain: "cross-squad coordination"
confidence: "medium"
source: "manual"
---

## Context

FitTrack has two squads in two repos: `fittrack-backend` (`fitness-backend/`) and
`fittrack-frontend` (`fitness-tracker/`). They share no runtime. The only thing both sides build
against is the API contract: `openapi.json` at the root of the backend repo.

Use this skill whenever a task adds, changes, removes or consumes an API endpoint, request body,
response field or error shape.

The owner is not part of this protocol. Do not ask the owner to approve a contract. Do not wait for
a merge. The two Leads decide.

## Patterns

### A feature needs both repos (the normal case)

1. Frontend Product writes the PRD and splits it by squad.
2. Frontend runs `squad delegate fittrack-backend "<purpose, fields needed, acceptance criteria,
   link to the frontend issue>"`. This opens a `[cross-squad]` issue in the backend repo.
3. Frontend opens its own UI issue in the frontend repo with labels `squad` and `status:blocked`,
   and a comment: `Waiting on bshaver3/Fitness-backend#N for the contract.`
   Frontend work that does not need the contract (PRD, UX spec, test cases) continues now.
4. The backend watcher picks up the delegated issue. Backend Lead decides the shape, regenerates
   `openapi.json`, and pushes it to the feature branch as the **first commit**.
5. Backend immediately unblocks the frontend. On the frontend issue it posts the branch name and a
   summary of the shape, then removes `status:blocked`:
   `gh issue edit <n> --repo bshaver3/fitness-tracker --remove-label status:blocked`
6. Both squads now build in parallel. Backend implements and tests on the same branch. Frontend
   reads the contract from the backend branch:
   `git -C ../fitness-backend fetch origin && git -C ../fitness-backend show origin/<branch>:openapi.json`
7. Each squad opens one PR with `Closes #N`, gets agent reviews, then labels its issue
   `status:on-hold`. The owner merges both PRs. Backend merges first.

### The shape changes after the frontend started

Backend updates `openapi.json` on the same branch and comments on the frontend issue with the exact
diff. Frontend adapts. No new issue, no approval.

### Frontend finds a problem in the contract

Frontend comments on the backend issue with the mismatch and a proposed fix, then continues with
work that the mismatch does not affect. Backend Lead answers on the issue and updates the branch.

### Backend wants to change an existing, already merged shape

1. Backend Lead checks which frontend callers use it (read `../fitness-tracker/src/`, read-only).
2. Additive change (new optional field, new endpoint): update `openapi.json`, then run
   `squad delegate fittrack-frontend "<what changed and why>"` so the frontend can adopt it.
3. Breaking change (remove, rename, retype, new required field): open the cross-squad issue
   first. Frontend Lead signs off on the issue. Ship the frontend change before removing the old
   shape. If the two Leads cannot agree, label the issue `status:blocked` and ask the owner there.

### Keeping `openapi.json` honest

- Regenerate it from the running FastAPI app; do not hand-edit shapes.
- Backend Tester keeps a contract test that fails when the app and the committed file differ.
- A backend PR that changes a route or model without the matching `openapi.json` diff is rejected.

### Local end-to-end check

Backend: `LOCAL_MOCK=true uvicorn main:app --reload --port 8000`.
Frontend: `REACT_APP_MOCK_AUTH=true npm start`.
Both use the `local-dev-user` identity, so no Cognito access is needed.

## Anti-Patterns

- Asking the owner to approve a contract, or waiting for a PR to merge before starting.
- A separate contract-only PR. The contract goes in the feature PR.
- Leaving the other squad's issue `status:blocked` after the thing it waits on exists.
- Closing an issue by hand before its PR merges.
- Frontend inventing a field, or computing a value the API should own, to avoid a delegation.
- Backend changing a response shape "because nothing uses it" without checking the frontend repo.
- Editing files in the other squad's repo.
- Agreeing a shape in chat only. If it is not in `openapi.json`, it is not agreed.
- Open-ended cross-squad issues without acceptance criteria.
