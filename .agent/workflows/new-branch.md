---
description: Create and switch to a new Git branch safely.
---

1. **Check current Git status**
   - Run `git status`.
   - If uncommitted changes exist, ask user whether to commit, stash, or cancel.

2. **Determine new branch name**
   - If provided in the request (e.g. "create branch foo"), use it.
   - Otherwise, **ask the user** for the new branch name.

3. **Create and switch**
   - Run `git checkout -b <branch-name>`.

4. **Confirm**
   - Run `git branch` to verify.
