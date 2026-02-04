---
description: Create a PR to dev, wait for checks, and optionally merge.
---

1. **Verify branch state**
   - Run `git branch --show-current` and `git status --porcelain`.
   - If on `dev`, stop and ask user to create a feature branch.
   - If uncommitted changes, run `/git-commit` flow first.
   - If branch not pushed, push with `git push -u origin HEAD`.

2. **Check for existing PR**
   - Run `gh pr list --head <branch> --base dev`.
   - If open PR exists, use it instead of creating a new one.

3. **Create the PR**
   - Generate title and body from commits and diff.
   - Run `gh pr create --base dev --head <branch> --title "<title>" --body "<body>"`.

4. **Wait for GitHub checks**
   - Run `gh pr checks <PR_NUMBER> --watch` (max 5 minutes).
   - Report check status to user.
   - If checks fail, stop and report.

5. **Merge (only if `merge` parameter passed)**
   - Verify PR is mergeable.
   - Run `gh pr merge <PR_NUMBER> --squash --delete-branch`.
   - If merge fails (reviews required, conflicts), stop and report.

6. **Final summary**
   - Report PR URL and status.
   - If merged, confirm branch deletion.
