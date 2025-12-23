---
description: Generate a safe, high-quality commit with minimal user intervention.
---

1. **Analyze the working tree**
   - Run `git status` and `git diff --stat`.
   - If there are **no changes**, stop and inform the user.
   - Generate a natural-language summary of changes (files, nature, sensitive files, etc.).
   - If you detect *potential risk* (many deletions, config changes, etc.), STOP and ask for confirmation.

2. **Stage changes**
   - Run `git add .`

3. **Run project checks (mandatory)**
   - Check if `eslint` exists, if so run `npx eslint .` (or equivalent).
   - Check for other linters/tests (TypeScript `tsc`, `flake8`, etc.) and run them.
   - If any check fails, STOP and ask the user to fix issues.

4. **Auto-generate the commit message**
   - Create a message with an emoji, conventional commit prefix (feat, fix, etc.), and a summary.
   - Example: `🛠 chore: update workflows`

5. **Create the commit**
   - Run `git commit -m "<generated-message>"`

6. **Push the commit automatically**
   - Check if branch tracks a remote.
   - If first push: `git push -u origin <current-branch>`
   - Otherwise: `git push`
   - If push fails, stop and report error.

7. **Final status**
   - Run `git status` to confirm clean tree.
