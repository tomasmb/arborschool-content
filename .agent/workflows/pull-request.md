---
description: Prepare and create a Pull Request via GitHub CLI.
---

1. **Check working tree and current branch**
   - Run `git status` and `git branch --show-current`.
   - If uncommitted changes exist, stop and ask user to commit/stash.
   - If on `main` or `master`, stop and ask user to switch to a feature branch.

2. **Ensure the branch is pushed**
   - Run `git status -sb`.
   - If ahead of origin, push it (`git push` or `git push -u origin <branch>`).

3. **Check GitHub CLI (`gh`) setup**
   - Verify `gh` is installed and authenticated (`gh auth status`).
   - If not, stop and guide user.

4. **Generate PR title and body**
   - Inspect commits (`git log -5 --oneline`) and diff.
   - Generate a clear Title and Markdown Body.
   - Show them to the user and **ask for confirmation** before proceeding.

5. **Create the PR**
   - If confirmed, run `gh pr create --base main --head <current-branch> --title "<title>" --body "<body>"`.
   - Retrieve and display the PR URL.

6. **Final recap**
   - Confirm success and share the link.
