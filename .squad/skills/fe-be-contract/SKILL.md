---
name: "fe-be-contract"
description: "How the FitTrack backend and frontend squads agree, change and consume the API contract so the two repos never drift apart."
domain: "cross-squad coordination"
confidence: "medium"
source: "copied from fittrack-shared upstream (parent folder .squad/skills/fe-be-contract); edit there, then re-copy"
---

## Context

FitTrack has two squads in two repos: `fittrack-backend` (`fitness-backend/`) and
`fittrack-frontend` (`fitness-tracker/`). They share no runtime. The only thing both sides build
against is the API contract: `openapi.json` at the root of the backend repo.

Use this skill whenever a task adds, changes, removes or consumes an API endpoint, request body,
response field or error shape.

## Patterns

### Frontend needs something the contract does not have

1. Frontend Lead writes the request: endpoint purpose, fields needed, example response, the
   acceptance criteria from the PRD.
2. Frontend coordinator runs `squad delegate fittrack-backend "<request>"`. This opens a
   `[cross-squad]` issue in the backend repo.
3. Backend Lead triages it, replies on the issue with the proposed shape, and updates
   `openapi.json` in a small contract-only PR.
4. After that PR merges, both squads build in parallel: backend implements, frontend builds
   against the contract using the mock backend.
5. Backend closes the issue when the endpoint ships. Frontend then removes any mock data.

### Backend wants to change an existing shape

1. Backend Lead checks which frontend callers use it (read `../fitness-tracker/src/`, read-only).
2. Additive change (new optional field, new endpoint): update `openapi.json`, then run
   `squad delegate fittrack-frontend "<what changed and why>"` so the frontend can adopt it.
3. Breaking change (remove, rename, retype, new required field): open the cross-squad issue
   first. Do not merge until the frontend Lead signs off on the issue. Ship the frontend change
   before removing the old shape.

### Keeping `openapi.json` honest

- Regenerate it from the running FastAPI app; do not hand-edit shapes.
- Backend Tester keeps a contract test that fails when the app and the committed file differ.
- A backend PR that changes a route or model without the matching `openapi.json` diff is rejected.

### Local end-to-end check

Backend: `LOCAL_MOCK=true uvicorn main:app --reload --port 8000`.
Frontend: `REACT_APP_MOCK_AUTH=true npm start`.
Both use the `local-dev-user` identity, so no Cognito access is needed.

## Anti-Patterns

- Frontend inventing a field, or computing a value the API should own, to avoid a delegation.
- Backend changing a response shape "because nothing uses it" without checking the frontend repo.
- Editing files in the other squad's repo.
- Agreeing a shape in chat only. If it is not in `openapi.json`, it is not agreed.
- Open-ended cross-squad issues without acceptance criteria.
