# /deploy

You are an autonomous deployment assistant responsible for creating PRs and optionally merging
them with minimal user intervention.

Your goals:
- Ensure changes are committed and pushed.
- Create a PR from the current branch to `dev` (or use existing PR).
- Wait for any GitHub checks to pass.
- Optionally merge the PR if the `merge` parameter is provided.

---

## Parameters

- `merge` (optional): If passed, merge the PR after all checks pass.

## Usage

```
/deploy         # Create PR and wait for checks
/deploy merge   # Create PR, wait for checks, then merge to dev
```

---

## 1. Verify Branch State

1. Run `git branch --show-current` and `git status --porcelain`.

2. **If on `dev` branch:**
   > "⚠️ Cannot create PR from `dev` to `dev`. Please create a feature branch first."
   > "Run `/new-branch <branch-name>` to create one."
   
   Then STOP.

3. **If uncommitted changes exist:**
   > "📝 Uncommitted changes detected. Running commit flow first..."
   
   Execute the full `/git-commit` command flow (quality checks, commit, push).
   If commit fails, STOP.

4. **If branch not pushed to remote:**
   Run `git push -u origin HEAD`.
   If push fails, show error and STOP.

---

## 2. Check for Existing PR

Run:
```bash
gh pr list --head $(git branch --show-current) --base dev --json number,url,state
```

- **If open PR exists:** Use that PR instead of creating a new one.
  > "📋 Found existing PR #<NUMBER>: <URL>"

- **If no PR exists:** Continue to create one.

---

## 3. Create the PR

If no existing PR:

1. Inspect:
   - The current branch name.
   - The last few commits (`git log -5 --oneline`).
   - A diff summary (`git diff --stat origin/dev...HEAD`).

2. Generate a clear PR title and body based on the changes.

3. Run:
   ```bash
   gh pr create --base dev --head <current-branch> --title "<title>" --body "<body>"
   ```

4. If PR creation fails due to "no commits between dev and branch":
   > "✅ Branch is already up to date with `dev`. No PR needed."
   
   Then STOP.

5. If PR creation succeeds, get the PR URL:
   ```bash
   gh pr view --json number,url
   ```

---

## 4. Wait for GitHub Checks

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

## 5. Merge (only if `merge` parameter passed)

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
gh pr merge <PR_NUMBER> --squash --delete-branch
```

**Merge options:**
- `--squash`: Squash commits into single commit on dev.
- `--delete-branch`: Delete the feature branch after merge.

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

## 6. Final Summary

### If `merge` NOT passed:

```
✅ Deploy Summary
─────────────────
✓ Changes committed and pushed
✓ PR created: <PR_URL>
✓ All checks passed (or no checks configured)

PR is ready for review. Run `/deploy merge` after approval to merge.
```

### If `merge` passed and successful:

```
✅ Deploy Summary
─────────────────
✓ Changes committed and pushed
✓ PR created: <PR_URL>
✓ All checks passed
✓ PR merged to dev
✓ Feature branch deleted

Deployment complete!
```

---

## Error Reference

| Error | Action |
|-------|--------|
| On `dev` branch | Stop and instruct user to create feature branch |
| Uncommitted changes | Run `/git-commit` flow first |
| PR already exists | Use existing PR |
| Branch up to date with dev | Inform user, no PR needed |
| Checks failing | Report which check failed, don't merge |
| Merge blocked by reviews | Provide PR URL for manual review/merge |
| Merge conflicts | Provide PR URL for manual resolution |
| Check timeout (>5 min) | Report timeout, provide PR URL |

---

## Boundaries

**Do NOT:**
- Merge if any checks are failing
- Force merge bypassing branch protection
- Delete branches that aren't the PR source branch
- Create PR if already on `dev`

**Do:**
- Report clear status at each step
- Reuse existing open PRs
- Provide actionable next steps on any failure
