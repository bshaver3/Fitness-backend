# Lead — History

## Core Context

- **Role:** Lead / Architect
- **Joined:** 2026-11-14
- **Owner:** Brendan
- **Project:** FitTrack: a website that tracks each user's workouts, calories and food intake, then suggests attainable workouts and diet plans based on their fitness goals and physique.
- **This repo:** FastAPI backend (`main.py`, `auth.py`), deployed to Elastic Beanstalk behind API Gateway.
- **Stack:** Python 3.11, FastAPI, Pydantic v2, boto3/DynamoDB (Workouts, UserProfiles, PlannedWorkouts), Cognito JWT auth, ruff, gunicorn+uvicorn, Elastic Beanstalk, API Gateway.
- **Peer squad:** `fittrack-frontend` (frontend, sibling repo `../fitness-tracker`)
- **Known gaps at start:** no test suite; no CI; all routes and models in one 792-line `main.py`; no food or calorie-intake endpoints; no recommendation engine; `.venv/` is tracked in git.

## Learnings

<!-- Append new learnings below -->
