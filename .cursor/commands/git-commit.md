# /git-commit

You are helping me create **clean, safe Git commits** in this repository.

## Goal
Review my changes, warn me of any risk, run basic checks, and then create a descriptive commit with an emoji.

## Behavior

When I call `/git-commit`, follow these steps:

1. **Show Git status**
   - Run: `git status`
   - Show me:
     - which files are modified
     - which files are untracked
   - Ask:
     > "These are the current changes. Do you want to include ALL of them in this commit? (yes/no)"

2. **If I answer "no"**
   - Help me choose which files to stage.
   - Ask:
     > "Which files do you want to stage? (you can list them by name)"
   - Then run `git add <file1> <file2> ...` accordingly.

3. **If I answer "yes"**
   - Run: `git add .`

4. **(Optional) Run checks**
   - If the project uses TypeScript, linting, or tests and I tell you which commands to use, run them here.
   - For now, ask:
     > "Do you want me to run any checks before committing? (e.g. tests, lint, TS compile) yes/no"
   - If "yes", ask which command to run (e.g. `npm test`, `npm run lint`) and execute it.
   - If checks fail, STOP and tell me:
     > "❌ Checks failed. Fix the issues before committing."

5. **Ask for a commit message**
   - Ask:
     > "Write a clear commit message (I will add an emoji in front if you want). For example:
     >  - '📘 Add PAES KG structure'
     >  - '🛠 Refactor atom granularity rules'
     >  - '✅ Fix atom generation validation'"
   - Wait for my message and use it as the commit message.

6. **Create the commit**
   - Run:
     - `git commit -m "<my-message>"`
   - If Git reports no staged changes, notify me:
     > "There were no staged changes to commit. Maybe you need to run `git add`?"

7. **Confirm**
   - Run `git status` again.
   - If everything is clean, say:
     > "✅ Commit created successfully with message: `<my-message>`"
   - If there are still unstaged changes, tell me what remains.
