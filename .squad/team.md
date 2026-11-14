# Squad Team

> FitTrack API: workouts, food intake, profiles, insights and the recommendation engine

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| Lead | Lead / Architect | `.squad/agents/lead/charter.md` | ✅ Active |
| Backend | Backend Developer | `.squad/agents/backend/charter.md` | ✅ Active |
| Coach | Recommendation Engineer | `.squad/agents/coach/charter.md` | ✅ Active |
| Tester | Test Engineer | `.squad/agents/tester/charter.md` | ✅ Active |
| Security | Security Engineer | `.squad/agents/security/charter.md` | ✅ Active |
| DevOps | DevOps Engineer | `.squad/agents/devops/charter.md` | ✅ Active |
| Docs | Technical Writer | `.squad/agents/docs/charter.md` | ✅ Active |

## Project Context

- **Owner:** Brendan
- **Squad:** fittrack-backend
- **Project:** FitTrack: a website that tracks each user's workouts, calories and food intake, then suggests attainable workouts and diet plans based on their fitness goals and physique.
- **This repo:** FastAPI backend (`main.py`, `auth.py`), deployed to Elastic Beanstalk behind API Gateway.
- **Stack:** Python 3.11, FastAPI, Pydantic v2, boto3/DynamoDB (Workouts, UserProfiles, PlannedWorkouts), Cognito JWT auth, ruff, gunicorn+uvicorn, Elastic Beanstalk, API Gateway.
- **Peer squad:** `fittrack-frontend` at `../fitness-tracker` (registered in `.squad/squad-registry.json`)
- **Shared context:** upstream `fittrack-shared` (parent folder `.squad/`): shared decisions, routing rules and the `fe-be-contract` skill
- **Created:** 2026-11-14
