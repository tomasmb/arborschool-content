# /new-branch

You are helping me manage Git branches in this repository.

## Goal
Create and switch to a **new Git branch** safely, following best practices.

## Behavior

When I call `/new-branch`, follow these steps:

1. **Check current Git status**
   - Run `git status`.
   - Show me the results.
   - If there are **uncommitted changes**, ask me:
     > "You have uncommitted changes. Do you want to:
     >  (a) commit them first,
     >  (b) stash them,
     >  (c) cancel branch creation?"
   - Wait for my answer and act accordingly.

2. **Ask for the new branch name (if not provided)**
   - If I wrote something like `/new-branch feature/standards-paes-m1`, use that as the branch name.
   - Otherwise, ask:
     > "What should the new branch be called? (e.g., `feature/standards-paes-m1`)"

3. **Create and switch to the new branch**
   - Run: `git checkout -b <branch-name>`
   - If there is any error, show it and help me fix it.

4. **Confirm**
   - Run `git branch` to confirm I'm on the new branch.
   - Say something like:
     > "✅ Switched to new branch `<branch-name>` and ready to work."
