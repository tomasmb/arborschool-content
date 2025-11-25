# /pull-request

You are helping me prepare a Pull Request for this branch.

## Goal
Push the current branch to GitHub and create a Pull Request against the `main` branch.

## Behavior

When I call `/pull-request`, follow these steps:

1. **Check Git status**
   - Run: `git status`
   - If there are uncommitted changes, ask:
     > "You still have uncommitted changes. Do you want to:
     >  (a) create a commit now with `/git-commit`,
     >  (b) cancel the PR and finish your work first?"
   - If I choose (b), stop the process.

2. **Identify the current branch**
   - Run: `git branch --show-current`
   - Show me the branch name:
     > "Current branch: `<branch-name>`"

3. **Push the branch**
   - Run:
     - `git push -u origin <branch-name>`
   - If the branch already exists remotely, run `git push` instead.
   - If there is any error (e.g. auth, conflicts), show it and help me fix it.

4. **Prepare the Pull Request**
   - Ask me for:
     - PR title
     - PR description
   - Suggest a reasonable default title based on the branch name (e.g. "Add PAES M1 standards file for atoms KG").

5. **Guide me to create the PR**
   - Tell me:
     > "Now go to GitHub → `Pull requests` → `New pull request` and choose:
     >  base: `main`
     >  compare: `<branch-name>`"
   - If GitHub integration is available, you may also help by constructing the PR via API, but otherwise just explain the steps.

6. **Confirm**
   - Once the PR is ready, summarize:
     > "✅ Pull Request prepared:
     >  - Branch: `<branch-name>`
     >  - Base: `main`
     >  - Title: `<title>`
     >  You can now request review from your teammate."
