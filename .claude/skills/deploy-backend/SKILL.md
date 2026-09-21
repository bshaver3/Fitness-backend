---
name: deploy-backend
description: Deploy fitness-backend to AWS Elastic Beanstalk with preflight checks, post-deploy verification, and rollback steps.
disable-model-invocation: true
argument-hint: "[environment-name]  (default: fitness-tracker-api)"
---

# Deploy fitness-backend to Elastic Beanstalk

Target environment: `$ARGUMENTS` if given, otherwise `fitness-tracker-api` (the environment the production API Gateway `fitness-tracker-api` / `cx2am009y6` proxies to). App: `fitness-backend`, region `us-east-1`. The EB CLI uses the `eb-cli` AWS profile (`.elasticbeanstalk/config.yml`); pass `--profile eb-cli --region us-east-1` to `aws` commands too.

Run the steps in order. **Stop and report to the user at the first failure**; don't work around a failed check. Deploying changes production, so show the preflight summary and get an explicit "yes" before step 3.

## 1. Preflight (read-only)

1. **Git state.** Must be on `main`, up to date with `origin/main`, with a clean working tree:
   ```bash
   git fetch origin && git status --short --branch
   ```
   This matters because `.ebignore` exists, so `eb deploy` uploads the **working directory**, not the last commit. Uncommitted or untracked files would ship.
2. **Lint.** `ruff format --check .` must pass. Run `ruff check .` and list any findings in the summary for the user to accept or not. Don't "fix" anything as part of a deploy.
3. **Mock-mode smoke test.** With `LOCAL_MOCK=true MOCK_DATA_FILE=<scratch path>`, use `fastapi.testclient.TestClient` from `.venv/bin/python` to check:
   - `GET /health` → 200
   - `POST /workouts` with `{"type":"running","duration":30,"calories":300}` → 200
   - `GET /insights/comprehensive` → 200

   Point `MOCK_DATA_FILE` outside the repo so no `mock-data.json` gets uploaded.
4. **Environment exists and is Ready:**
   ```bash
   aws elasticbeanstalk describe-environments --application-name fitness-backend --environment-names <env> --profile eb-cli --region us-east-1 --query 'Environments[].[EnvironmentName,Status,Health,CNAME,VersionLabel]' --output table
   ```
   - **No environment:** stop. Tell the user the environment is missing and that recreating it (`eb create`) is a separate decision with cost implications. A new environment gets a new CNAME, and the API Gateway integrations (`aws apigatewayv2 get-integrations --api-id cx2am009y6`) must be repointed to it afterwards.
   - **Status not `Ready`:** stop. A deploy fails with "invalid state for this operation. Must be Ready."
   - Otherwise, record the current `VersionLabel` as the rollback target.
5. **Cognito env vars are set** on the environment (the app can't verify tokens without them):
   ```bash
   aws elasticbeanstalk describe-configuration-settings --application-name fitness-backend --environment-name <env> --profile eb-cli --region us-east-1 --query "ConfigurationSettings[0].OptionSettings[?Namespace=='aws:elasticbeanstalk:application:environment'].OptionName" --output text
   ```
   It must include `COGNITO_USER_POOL_ID` and `COGNITO_APP_CLIENT_ID`. Print names only, never values.

Summarize for the user: commit SHA and message, target environment, current version (rollback target), and check results. Wait for confirmation.

## 2. Confirm

Deploy only after the user explicitly says yes to the summary.

## 3. Deploy

```bash
eb deploy <env> --label "$(git rev-parse --short HEAD)-$(date +%Y%m%d%H%M%S)" --timeout 20
```

A git-SHA label makes the deployed version traceable and gives a clean rollback target.

## 4. Verify

1. Environment is `Ready` and health is `Green` (re-run the command from preflight step 4). If it's `Yellow`/`Red`, check `eb events <env>` and `eb logs <env>`.
2. Directly: `curl -s -o /dev/null -w '%{http_code}' http://<CNAME>/health` → `200`.
3. Through production API Gateway: `curl -s -o /dev/null -w '%{http_code}' https://cx2am009y6.execute-api.us-east-1.amazonaws.com/health` → `200`.
4. Auth is enforced: `curl -s -o /dev/null -w '%{http_code}' https://cx2am009y6.execute-api.us-east-1.amazonaws.com/workouts` (no token) → `401` or `403`, **not** 200 or 500.

## 5. Roll back if verification fails

Tell the user what failed, then offer (don't run without a yes):
```bash
eb deploy <env> --version <previous VersionLabel from preflight>
```
Re-run step 4 afterwards.

## Report

End with: deployed version label, commit, environment health, and the result of each verification check.
