# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

FastAPI backend for the FitTrack app. The React frontend lives in a sibling repo at `../fitness-tracker` (GitHub `bshaver3/fitness-tracker`); endpoint changes here usually need a matching change in its `src/api.js` callers.

## Commands

```bash
source .venv/bin/activate          # Python 3.11 venv
pip install -r requirements.txt

# Local dev with no AWS access: JSON-file storage + fake auth
LOCAL_MOCK=true uvicorn main:app --reload --port 8000

# Local dev against real DynamoDB/Cognito (uses your AWS credentials)
COGNITO_USER_POOL_ID=us-east-1_fAO8zL6Gx COGNITO_APP_CLIENT_ID=<client id> uvicorn main:app --reload --port 8000

ruff format . && ruff check .      # formatting/lint (installed globally via Homebrew)
eb deploy                          # deploy to Elastic Beanstalk (app: fitness-backend, us-east-1)
```

There is no test suite yet. The frontend's `.env.development` points at `http://localhost:8000`.

Claude Code hooks (`.claude/settings.json`): edited `.py` files are auto-formatted with ruff; edits to `.env*`, `.venv/`, `.elasticbeanstalk/` are blocked; edits to `Procfile`, `.ebignore`, `.ebextensions/` require confirmation.

## Architecture

Everything lives in two files:

- `main.py` — app setup, middleware, Pydantic models, insight calculations, and all routes.
- `auth.py` — Cognito JWT verification. `get_current_user_id` is the dependency every protected route takes; it returns the token's `sub` claim.

**Mock mode (`LOCAL_MOCK=true`)** is switched at import time in both files:
- `auth.py` replaces `verify_token` with one that always returns `MOCK_USER_ID` (default `local-dev-user`, which matches the frontend's `REACT_APP_MOCK_AUTH` user).
- `main.py` swaps the three DynamoDB tables for `JsonTable`, a stand-in backed by `mock-data.json` (gitignored) that implements only `put_item`, `get_item`, `scan`, and `delete_item` with boto3-style keyword args. **Any new DynamoDB call must also be implemented in `JsonTable`**, or mock mode breaks. Its `scan` ignores `FilterExpression` and only filters on `ExpressionAttributeValues[':uid']`.

**Data model** — DynamoDB tables in us-east-1:

| Table | Partition key | Model |
|---|---|---|
| `Workouts` | `id` | `Workout` |
| `UserProfiles` | `user_id` | `Profile` |
| `PlannedWorkouts` | `id` | `PlannedWorkout` |

Per-user lists use `scan` + a `user_id` filter; there are no GSIs and no pagination. Routes for single items fetch by `id`, then return 404 unless `item['user_id']` matches the caller — keep that ownership check on any new by-id route. Handlers always overwrite `user_id` from the token rather than trusting the request body. DynamoDB returns numbers as `Decimal`; `convert_decimal` handles that in the insight calculations.

**`GET /insights/comprehensive`** loads all of a user's workouts plus their profile (for weekly targets), then runs the `calculate_*` helpers to build the `ComprehensiveInsights` response that the frontend's Home and Insights pages chart.

## Conventions

- Request models are Pydantic v2 with `Field` bounds and `@field_validator`s. Enum-like fields are checked against module-level `ALLOWED_*` sets and normalized with `.strip().lower()`. New fields should follow the same pattern.
- Serialization to DynamoDB uses `.dict()`.
- Keep error details generic in `auth.py` (don't echo JWT/JWKS errors to clients).
- `RateLimitMiddleware` is in-memory (100 req/min per IP via `X-Forwarded-For`, 1 MB body cap), so limits apply per gunicorn worker/instance. `/` and `/health` are exempt.
- CORS `allow_origins` is hard-coded to `http://localhost:3000` and the production Amplify domain; a new frontend origin must be added there.

## Deployment

- Elastic Beanstalk, platform "Python 3.11 running on 64bit Amazon Linux 2023". `Procfile` runs gunicorn with uvicorn workers at `--log-level warning`.
- `COGNITO_USER_POOL_ID` / `COGNITO_APP_CLIENT_ID` (and optionally `COGNITO_REGION`) must be set as EB environment variables.
- `.ebignore` controls what is uploaded (excludes `.venv`, `workouts.db`, logs). `.ebextensions/python.config` sets a 30-minute command timeout.
- Git remotes: `origin` is GitHub (`bshaver3/Fitness-backend`, primary); `codecommit-origin` is a secondary CodeCommit remote.
- `workouts.db` (SQLite) and `latest_logs.txt` are unused leftovers, not part of the app.
