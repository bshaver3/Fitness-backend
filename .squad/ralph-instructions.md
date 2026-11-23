# Ralph Instructions
<!-- User-owned: customize this file to override Ralph's autonomous-execution behavior.
     squad init creates this file on first install; squad upgrade never overwrites it. -->

<!--
  PURPOSE
  -------
  When `.squad/ralph-instructions.md` exists, `squad watch --execute` instructs the
  spawned Copilot session to read this file and follow ALL sections here instead of
  the built-in fallback prompt.  If the file is absent, the built-in prompt is used.

  CONTRACT (stable — safe to build on)
  --------------------------------------
  YOU CAN  customize via this file:
    • Extra instructions given to Ralph at session start (Teams/Slack notifications,
      calendar checks, post-task hooks, MCP-powered side effects, escalation paths)
    • Additional eligibility rules or priority ordering for issue selection
    • Agent persona, tone, or verbosity for session output

  YOU CANNOT override via this file:
    • Parallelism — Ralph always spawns agents for all actionable issues simultaneously
    • Core eligibility filter (squad/squad:* label required, not blocked, not assigned)
    • The underlying `gh` / Copilot CLI command used to spawn each session

  TRUST IMPLICATIONS
  ------------------
  This file is read by the spawned Copilot session with full agent permissions.
  Treat it like code — never paste untrusted content here.  Anyone with write access
  to this file can influence what the agent does on your behalf.

  If this file is missing or empty, `squad watch --execute` falls back to the
  built-in prompt with no behavioral change.

  PLACEHOLDERS
  ------------
  The following values are injected by execute.ts before the session reads this file:
    (none currently — Ralph builds the issue list dynamically at runtime)

  FORMAT
  ------
  Plain markdown.  Structure with ## sections.  The spawned session reads the whole
  file, so keep it concise — one screen of instructions is ideal.
-->

## Ralph, Go!

Read this file for your full instructions.  Follow ALL sections.
MAXIMIZE PARALLELISM — spawn agents for ALL actionable issues simultaneously.

This session is unattended. The owner is not watching. Never stop to ask the owner a question
and never wait for an owner approval. Read `.squad/decisions.md` and
`.squad/skills/fe-be-contract/SKILL.md` first; they define the flow.

### Issue Selection

Work on every open, unassigned issue labeled `squad` or `squad:{member}` that has no
`status:blocked` and no `status:on-hold` label. An issue that already has a branch or a PR is a
continuation: check out that branch and finish it. Do not start a second branch.

### Working an Issue

1. Lead triages and names the members. No approval step follows triage. GitHub does not triage
   by keyword any more, so Lead sets the member label: `gh issue edit <n> --add-label squad:<member>`
   for the member who owns most of the work (for example `squad:backend`). Keep the `squad` label.
   If the issue already has a wrong `squad:<member>` label, remove it in the same command.
2. Work on one branch per issue: `squad/<issue-number>-<slug>`, created from fresh `origin/main`.
3. API shape involved: follow the `fe-be-contract` skill. Contract commit first, then unblock the
   other squad, then build.
4. Run the reviews the charters require (Lead, Tester, Security, Fact Checker, Rai) inside this
   session. Fix what they reject. Do not ask the owner to arbitrate.
5. Run the repo's lint and tests before the PR.

### Handoffs to the Other Squad (fittrack-frontend)

- Need work from them: `squad delegate fittrack-frontend "<request + acceptance criteria + link to this issue>"`.
  Then label this issue `status:blocked` and comment which issue it waits on. Continue any part
  that does not depend on them before you block.
- Your work unblocks one of their issues: comment there, then
  `gh issue edit <n> --repo bshaver3/fitness-tracker --remove-label status:blocked`.
- Never edit files in `../fitness-tracker`. Reading is fine.

### Post-Task Actions

When the work for an issue is complete:
- Open one PR against `main` with `Closes #<issue>` in the body and a short test summary.
- Label the issue `status:on-hold` (`gh issue edit <n> --add-label status:on-hold`). This means
  "waiting for owner merge" and stops the watcher from re-running it.
- Do not close the issue. Do not merge the PR. Do not assign the issue to anyone.
- Do not apply a `squad:cross-squad` label; it is not a team member.
- Return to `main` (`git checkout main`) so the next watcher round starts clean.

### Escalation

If you are blocked by something no agent in either squad can resolve (a missing secret, a
mutating AWS command, a breaking contract change the two Leads disagree on), comment on the issue
with the exact question or command for the owner, add `status:blocked`, and move to the next
actionable item.  Do not halt the loop.
