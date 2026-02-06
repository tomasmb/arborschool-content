# /deploy

You are an autonomous deployment assistant responsible for creating PRs and optionally merging
them with minimal user intervention.

Your goals:
- Ensure changes are committed and pushed.
- Create a PR from `dev` to `main` (or use existing PR).
- Wait for any GitHub checks to pass.
- Optionally merge the PR if the `merge` parameter is provided.

---

## Parameters

- `merge` (optional): If passed, merge the PR after all checks pass.

## Usage

```
/deploy         # Create PR from dev to main and wait for checks
/deploy merge   # Create PR, wait for checks, then merge to main
```

---

## 1. Verify Branch State

1. Run `git branch --show-current` and `git status --porcelain`.

2. **If NOT on `dev` branch:**
   > "⚠️ Deploy creates PRs from `dev` to `main`. Please switch to `dev` first."
   > "Run `git checkout dev` to switch."
   
   Then STOP.

3. **If uncommitted changes exist:**
   > "📝 Uncommitted changes detected. Running commit flow first..."
   
   Execute the full `/git-commit` command flow (quality checks, commit, push).
   If commit fails, STOP.

4. **If branch not pushed to remote:**
   Run `git push -u origin HEAD`.
   If push fails, show error and STOP.

---

## 2. Sync Both Branches and Merge Main into Dev (CRITICAL)

**This step ensures both branches are up to date and conflict-free before opening a PR.**

1. Fetch latest from origin (both branches):
   ```bash
   git fetch origin main dev
   ```

2. Fast-forward local dev to match remote:
   ```bash
   git pull --ff-only origin dev
   ```
   - If this fails (diverged history), STOP and warn the user.

3. Merge origin/main into dev:
   ```bash
   git merge origin/main --no-edit
   ```

4. **If merge conflicts occur → STOP immediately.**
   Do NOT attempt to auto-resolve. Show the conflicted files and say:
   > "❌ Merge conflicts detected when merging main into dev."
   > "Conflicted files: ..."
   > "Please resolve manually, then run `/deploy` again."
   
   Then abort the merge:
   ```bash
   git merge --abort
   ```
   Then STOP.

5. **Push the merge (only if clean):**
   ```bash
   git push
   ```

6. **If already up to date:**
   > "✓ dev is up to date with main"

---

## 3. Check for Existing PR

Run:
```bash
gh pr list --head dev --base main --json number,url,state
```

- **If open PR exists:** Use that PR instead of creating a new one.
  > "📋 Found existing PR #<NUMBER>: <URL>"

- **If no PR exists:** Continue to create one.

---

## 4. Create the PR

If no existing PR:

1. Inspect:
   - The commits on dev not yet on main (`git log origin/main..origin/dev --oneline`).
   - A diff summary (`git diff --stat origin/main...origin/dev`).

2. Generate a clear PR title and body based on the changes.

3. Run:
   ```bash
   gh pr create --base main --head dev --title "<title>" --body "<body>"
   ```

4. If PR creation fails due to "no commits between main and dev":
   > "✅ `main` is already up to date with `dev`. No PR needed."
   
   Then STOP.

5. If PR creation succeeds, get the PR URL:
   ```bash
   gh pr view --json number,url
   ```

---

## 5. Wait for GitHub Checks

Monitor the PR checks until all complete:

```bash
gh pr checks <PR_NUMBER> --watch
```

**Alternative polling (if --watch times out or isn't available):**

```bash
gh pr view <PR_NUMBER> --json statusCheckRollup
```

### Polling Strategy

1. Check status every 15 seconds.
2. Maximum wait time: 5 minutes.
3. Report progress to user:
   - "⏳ Waiting for checks to complete..."
   - "✓ Check `<name>` passed"
   - "✅ All checks passed!"

### If No Checks Configured

If the repo has no CI checks, the PR will show as ready immediately:
> "ℹ️ No CI checks configured for this repo. PR is ready."

### If Checks Fail

If any check fails:
> "❌ Check `<name>` failed. Please fix the issues before merging."
> "PR URL: <URL>"

Then STOP (do not merge).

---

## 6. Merge (only if `merge` parameter passed)

If the user did NOT pass `merge`, skip this section and go to Final Summary.

### Pre-Merge Verification

Before merging, verify:
1. All checks have passed.
2. PR is in mergeable state.

```bash
gh pr view <PR_NUMBER> --json mergeable,mergeStateStatus
```

### Perform Merge

```bash
gh pr merge <PR_NUMBER> --squash
```

**Merge options:**
- `--squash`: Squash commits into single commit on main.
- Note: We do NOT delete dev branch after merge.

### If Merge Fails

**If merge fails due to review requirement:**
> "⚠️ PR requires approval before merging."
> "Please get a review or merge manually: <PR_URL>"

Then STOP.

**If merge fails due to merge conflicts:**
> "⚠️ PR has merge conflicts. Please resolve them first."
> "PR URL: <PR_URL>"

Then STOP.

---

## 7. Final Summary

### If `merge` NOT passed:

```
✅ Deploy Summary
─────────────────
✓ PR created: <PR_URL>
✓ All checks passed (or no checks configured)

PR is ready for review. Run `/deploy merge` after approval to merge to main.
```

### If `merge` passed and successful:

```
✅ Deploy Summary
─────────────────
✓ PR created: <PR_URL>
✓ All checks passed
✓ PR merged to main

Deployment complete!
```

---

## Error Reference

| Error | Action |
|-------|--------|
| Not on `dev` branch | Stop and instruct user to switch to dev |
| Uncommitted changes | Run `/git-commit` flow first |
| PR already exists | Use existing PR |
| main up to date with dev | Inform user, no PR needed |
| Checks failing | Report which check failed, don't merge |
| Merge blocked by reviews | Provide PR URL for manual review/merge |
| Merge conflicts | Provide PR URL for manual resolution |
| Check timeout (>5 min) | Report timeout, provide PR URL |

---

## Boundaries

**Do NOT:**
- Merge if any checks are failing
- Force merge bypassing branch protection
- Delete the dev branch after merge
- Create PR if not on `dev`

**Do:**
- Report clear status at each step
- Reuse existing open PRs
- Provide actionable next steps on any failure
