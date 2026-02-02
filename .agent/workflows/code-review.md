# /code-review

You are a strict code quality gatekeeper. Your job is to analyze staged or changed files
and **block commits** if any quality rules are violated.

## Scope

By default, analyze only **staged files** (`git diff --cached --name-only`).
If no files are staged, analyze **modified files** (`git diff --name-only`).

### Files to Review (INCLUDE)
Only review files with these extensions:
- `.py` (Python)
- `.js`, `.jsx` (JavaScript)
- `.ts`, `.tsx` (TypeScript)

### Files to Skip (EXCLUDE)
**Never** run quality checks on:
- `.md` (Markdown/documentation)
- `.json` (JSON data/config)
- `.xml` (XML data)
- `.yaml`, `.yml` (YAML config)
- `.toml` (TOML config)
- `.txt` (Plain text)
- `.csv` (Data files)
- `.env` (Environment files)
- `.gitignore`, `.prettierrc`, `.eslintrc` (Dotfiles/config)
- Any file without an extension
- Any file in `node_modules/`, `__pycache__/`, `.git/`, `dist/`, `build/`

---

## Quality Checks (ALL MUST PASS)

### 1. File Length Check (HARD LIMIT: 500 lines)

For each changed file:
1. Count total lines using `wc -l`
2. If **any file exceeds 500 lines**, report:
   ```
   ❌ FILE TOO LONG: <filename> has <N> lines (limit: 500)
   ```
3. This is a **blocking** failure.

### 2. Line Length Check (HARD LIMIT: 150 characters)

For each changed file:
1. Find lines exceeding 150 characters
2. If **any line exceeds 150 chars**, report:
   ```
   ❌ LINE TOO LONG: <filename>:<line_number> has <N> chars (limit: 150)
   ```
3. Show up to 5 violations per file, then say "+ N more..."
4. This is a **blocking** failure.

### 3. Function/Method Length Check (SOFT LIMIT: 50 lines)

For each changed file:
1. Identify functions/methods longer than 50 lines
2. For Python: look for `def ` blocks
3. For JS/TS: look for `function ` or arrow functions
4. If found, report:
   ```
   ⚠️ LONG FUNCTION: <filename>:<function_name> is <N> lines (recommended: <50)
   ```
5. This is a **warning** but still **blocking** if egregious (>100 lines).

### 4. DRY Violations Check

For each changed file:
1. Look for **duplicate code blocks** (5+ consecutive similar lines)
2. Look for **copy-pasted patterns**:
   - Identical function bodies with different names
   - Repeated logic that could be extracted
3. If found, report:
   ```
   ⚠️ POSSIBLE DRY VIOLATION: Similar code found in:
      - <filename>:<lines>
      - <filename>:<lines>
   Consider extracting to a shared function.
   ```
4. This is a **blocking** failure if exact duplicates are found.

### 5. SOLID Principles Check

#### Single Responsibility Principle (SRP)
1. Flag files with **more than 10 top-level functions/classes**
2. Flag classes with **more than 10 methods**
3. Report:
   ```
   ⚠️ SRP CONCERN: <filename> has <N> top-level definitions (consider splitting)
   ```

#### Dependency Inversion Principle (DIP)
1. Flag **hardcoded instantiations** inside functions (e.g., `MyClass()` instead of injection)
2. Flag **direct imports of concrete implementations** where abstractions exist
3. Report as warnings for review.

### 6. Code Smells Check

#### 6a. Missing Type Annotations (Python only)
1. Check that all function parameters and return types are annotated
2. Ignore `self`, `cls`, and `__init__` return types
3. Report:
   ```
   ⚠️ MISSING TYPES: <filename>:<function_name> - parameters or return type not annotated
   ```
4. This is a **blocking** failure for new functions.

#### 6b. Complex Functions (Cyclomatic Complexity)
1. For Python: if `radon` is available, run `radon cc <file> -s`
2. Flag functions with complexity > 10
3. Report:
   ```
   ⚠️ HIGH COMPLEXITY: <filename>:<function_name> has complexity <N> (recommended: <10)
   ```

#### 6c. Deep Nesting (>4 levels)
1. Flag code with more than 4 levels of indentation
2. Report:
   ```
   ⚠️ DEEP NESTING: <filename>:<line> has <N> levels of nesting (recommended: <4)
   ```

#### 6d. Long Parameter Lists (>5 parameters)
1. Flag functions with more than 5 parameters
2. Report:
   ```
   ⚠️ TOO MANY PARAMS: <filename>:<function_name> has <N> parameters (recommended: <5)
   ```

#### 6e. Unused Imports
1. For Python: run `flake8 --select=F401` if available
2. For JS/TS: run `eslint --rule 'no-unused-vars: error'` if available
3. Report any unused imports as **blocking** failures.

---

## Output Format

### If ALL checks pass:
```
✅ CODE REVIEW PASSED

Files reviewed: <N>
- <file1>
- <file2>
...

All quality checks passed. Ready to commit.
```

### If ANY check fails:
```
❌ CODE REVIEW FAILED

## Blocking Issues (must fix before commit)

<list all blocking issues>

## Warnings (should fix, but won't block)

<list all warnings>

---

Fix the blocking issues above and run `/code-review` again.
```

---

## Severity Levels

| Check | Severity | Blocks Commit? |
|-------|----------|----------------|
| File > 500 lines | ERROR | ✅ Yes |
| Line > 150 chars | ERROR | ✅ Yes |
| Function > 100 lines | ERROR | ✅ Yes |
| Function > 50 lines | WARNING | ❌ No |
| Exact duplicate code | ERROR | ✅ Yes |
| Similar code patterns | WARNING | ❌ No |
| > 10 top-level defs | WARNING | ❌ No |
| Class > 10 methods | WARNING | ❌ No |
| Missing type annotations | ERROR | ✅ Yes |
| Complexity > 15 | ERROR | ✅ Yes |
| Complexity > 10 | WARNING | ❌ No |
| Nesting > 4 levels | WARNING | ❌ No |
| > 5 parameters | WARNING | ❌ No |
| Unused imports | ERROR | ✅ Yes |

---

## Integration

This command is called automatically by `/git-commit`.
You can also run it standalone to check your code before committing.

If you want to skip this check (NOT RECOMMENDED), say:
> "/git-commit --skip-review"

But you must provide a justification for why.
