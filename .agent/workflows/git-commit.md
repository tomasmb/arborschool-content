---
description: Generate a safe, high-quality commit with minimal user intervention. Runs code quality checks before committing.
---

1. **Analyze the working tree**
   - Run `git status` and `git diff --stat`.
   - If there are **no changes**, stop and inform the user.
   - Generate a natural-language summary of changes (files, nature, sensitive files, etc.).
   - If you detect *potential risk* (many deletions, config changes, etc.), STOP and ask for confirmation.

2. **Stage changes**
   - Run `git add .`

3. **Run CODE_STANDARDS checks (mandatory)**
   
   > Reference: `docs/specifications/CODE_STANDARDS.md`
   
   **a. Linting (Python)**
   // turbo
   - Run `ruff check app/` (or on modified Python files)
   - If errors exist, STOP and list them. Ask user to fix before continuing.
   
   **b. File size limits**
   - Check that all modified files are < 500 lines
   - If any exceed 500 lines, STOP and warn user to refactor.
   
   **c. Type hints (quick check)**
   - For new Python functions, verify they have type annotations
   - This is a best-effort check; report findings but don't block.
   
   **d. Prompt quality (if prompt files modified)**
   - If any prompt templates or LLM-related code was modified, verify:
     - No redundancy in instructions
     - No contradictions with existing rules
     - Structure is clear and segmented
   - Report findings but don't block (use judgment).

4. **Summary of quality checks**
   - Report status of all checks:
     ```
     ✅ Linting: passed
     ✅ File sizes: all < 500 lines
     ⚠️ Type hints: 2 functions missing annotations (non-blocking)
     ✅ Prompts: N/A
     ```
   - If any blocking check fails, STOP here.

5. **Auto-generate the commit message**
   - Create a message **ALWAYS** starting with an emoji, followed by conventional commit prefix (feat, fix, etc.), and a summary.
   - **Mandatory Emoji Mapping**:
     - feat: ✨
     - fix: 🐛
     - docs: 📚
     - style: 💎
     - refactor: 📦
     - perf: 🚀
     - test: 🚨
     - chore: 🛠
   - Example: `🛠 chore: update workflows`

6. **Create the commit**
   - Run `git commit -m "<generated-message>"`

7. **Push the commit automatically**
   - Check if branch tracks a remote.
   - If first push: `git push -u origin <current-branch>`
   - Otherwise: `git push`
   - If push fails, stop and report error.

8. **Final status**
   - Run `git status` to confirm clean tree.
   - Report that commit was successful with quality checks passed.
