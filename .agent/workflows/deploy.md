# /deploy

You are an autonomous deployment assistant. You create PRs from `dev` to `main`,
optionally merge them, and keep branches in sync afterward.

**CRITICAL CONTEXT**: This repo uses squash merges. After a squash merge,
`main` gets a new squash commit that `dev` doesn't have. If you don't
resync dev to main after merging, future deploys will have fake conflicts.

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
   > "⚠️ Deploy creates PRs from `dev` to `main`. Switch to `dev` first."

   Then STOP.

3. **If uncommitted changes exist:**
   > "📝 Uncommitted changes detected. Running commit flow first..."

   Execute the full `/git-commit` command flow.
   If commit fails, STOP.

4. **If branch not pushed to remote:**
   Run `git push -u origin HEAD`.
   If push fails, show error and STOP.

---

## 2. Sync Dev with Main (CRITICAL — prevents fake conflicts)

**Why this exists:** Squash merges cause `main` and `dev` to diverge in git
history even though the content is identical. This step fixes the divergence
BEFORE creating a PR, so the PR is always clean.

1. Fetch latest from origin:
   ```bash
   git fetch origin main dev
   ```

2. Check if main is ahead of dev (commits in main not in dev):
   ```bash
   git log dev..origin/main --oneline
   ```

3. **If main IS ahead** (has squash commits from a previous deploy):

   a. First, identify commits on dev that are NOT in main yet (your new work):
      ```bash
      git log origin/main..dev --oneline
      ```

   b. If dev has new commits not in main → rebase them onto main:
      ```bash
      git rebase origin/main
      ```
      - If rebase has conflicts → STOP, abort with `git rebase --abort`,
        and tell the user to resolve manually.
      - If rebase succeeds:
        ```bash
        git push --force-with-lease
        ```

   c. If dev has NO new commits (everything was already merged) → reset:
      ```bash
      git reset --hard origin/main
      git push --force-with-lease origin dev
      ```

4. **If main is NOT ahead:**
   > "✓ dev is up to date with main"

---

## 3. Check for Existing PR

Run:
```bash
gh pr list --head dev --base main --json number,url,state
```

- **If open PR exists:** Use that PR.
  > "📋 Found existing PR #NUMBER: URL"

- **If no PR exists:** Continue to create one.

---

## 4. Create the PR

If no existing PR:

1. Inspect:
   - Commits: `git log origin/main..origin/dev --oneline`
   - Diff: `git diff --stat origin/main...origin/dev`

2. If no commits between main and dev:
   > "✅ `main` is already up to date with `dev`. No PR needed."
   Then STOP.

3. Generate a clear PR title and body based on the changes.

4. Run:
   ```bash
   gh pr create --base main --head dev --title "<title>" --body "<body>"
   ```

5. Get the PR URL:
   ```bash
   gh pr view --json number,url
   ```

---

## 5. Wait for GitHub Checks

```bash
gh pr view <PR_NUMBER> --json statusCheckRollup
```

### Polling Strategy

1. Check status every 15 seconds.
2. Maximum wait time: 5 minutes.
3. Report progress:
   - "⏳ Waiting for checks..."
   - "✓ Check `<name>` passed"
   - "✅ All checks passed!"

### If No Checks Configured

> "ℹ️ No CI checks configured. PR is ready."

### If Checks Fail

> "❌ Check `<name>` failed. Fix the issues before merging."

Then STOP.

---

## 6. Merge (only if `merge` parameter passed)

If the user did NOT pass `merge`, skip to Final Summary.

### Pre-Merge Verification

```bash
gh pr view <PR_NUMBER> --json mergeable,mergeStateStatus
```

### Perform Merge

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch=false
```

### If Merge Fails

- **Review required:**
  > "⚠️ PR requires approval. Merge manually: <PR_URL>"
  STOP.

- **Merge conflicts:**
  > "⚠️ PR has merge conflicts. Resolve first: <PR_URL>"
  STOP.

---

## 7. Post-Merge: Resync Dev to Main (CRITICAL)

**This step MUST run after every squash merge. Skipping it causes fake
conflicts on the next deploy.**

After the squash merge succeeds:

```bash
git fetch origin main
git reset --hard origin/main
git push --force-with-lease origin dev
```

This makes dev identical to main, so the next round of work starts clean.

Report:
> "✓ dev branch reset to main (post-squash-merge sync)"

---

## 8. Final Summary

### If `merge` NOT passed:

```
✅ Deploy Summary
─────────────────
✓ PR created: <PR_URL>
✓ All checks passed (or no checks configured)

Run `/deploy merge` to merge to main.
```

### If `merge` passed and successful:

```
✅ Deploy Summary
─────────────────
✓ PR merged to main (squash)
✓ dev synced to main
Deployment complete!
```

---

## Error Reference

| Error | Action |
|-------|--------|
| Not on `dev` | Stop, instruct to switch |
| Uncommitted changes | Run `/git-commit` first |
| PR already exists | Use existing PR |
| main up to date with dev | No PR needed |
| Rebase conflicts | Abort, tell user to resolve |
| Checks failing | Report failure, don't merge |
| Merge blocked by reviews | Provide PR URL |

---

## Boundaries

**NEVER:**
- Merge if checks are failing
- Force merge bypassing branch protection
- Delete the dev branch
- Skip the post-merge resync (step 7)
- Try to auto-resolve merge/rebase conflicts

**ALWAYS:**
- Resync dev to main after every squash merge
- Use `--force-with-lease` (not `--force`) when pushing after rebase/reset
- Report clear status at each step
- STOP on any conflict and let the user decide
