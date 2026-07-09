---
name: gcp
version: 1.0.0
description: |
  Git Commit and Push with intelligent file grouping.
  Trigger this skill whenever the user says "commit", "push", "gcp", or anything related to git commit + push operations.
  This skill groups unstaged changes by feature/theme, commits each group separately, then pushes.
  Default is batch mode (all commits then one push); use -per for push-after-each-commit.
triggers:
  - /gcp
  - /gcp <message>
  - /gcp -batch
  - /gcp -per
  - /gcp -batch <message>
  - /gcp -per <message>
  - "commit and push"
  - "批量commit"
  - "分组commit"
---

# /gcp — Git Commit & Push with Smart Grouping

## Step 1: Analyze Changes

First, run these commands to understand the current state:

```bash
git status --short
git diff --stat
git diff --name-only
git log --oneline -5
```

If working tree is clean, skip to Step 7 (Pull + Push) — no commits needed, but still sync with remote.

### ⚠️ Git Diff Syntax Rule

When using `git diff` with **both options and paths**, options MUST come before paths, or use `--` separator:

```bash
# ✅ Correct
git diff --stat -- src/game_theory/
git diff --name-only -- src/routing/
git diff -- src/valuation/

# ❌ Wrong — options after path cause fatal error
git diff src/game_theory/ --stat        # fatal: --stat must come before non-option arguments
git diff src/routing/ --name-only       # same error
```

**Rule**: always place flags/options before paths, or use `--` to explicitly separate:
```
git diff [<options>] [--] [<path>...]
```

## Step 2: Group Files by Feature

Analyze the changed files and group them by **feature/theme** using these heuristics.

When inspecting specific directories, always use `git diff --stat -- <dir>/` (options before `--`):

1. **Same directory** → likely same feature
2. **Same file prefix** (e.g., `quiz_result_screen.dart`, `quiz_question_screen.dart`) → same feature
3. **Related concepts** in filenames (dream, quiz, profile, auth, share, etc.) → same feature
4. **UI-only changes** vs **logic-only changes** → may split into separate groups
5. **Single file** with many unrelated changes → single commit

## Step 3: Present Grouping Plan

Show the user the proposed grouping, then proceed directly without asking for confirmation.

Format:
```
Detected X file changes across N groups:

Group 1 — <Feature Name>:
  file1, file2, ...

Group 2 — <Feature Name>:
  file3, file4, ...

[Group N — ...]

Auto-committing and pushing...
```

Proceed directly to Step 4.

## Step 4: Determine Mode

Check user's input for flags:
- `/gcp -per` or `/gcp -per "message"` → **per-commit push mode**
- Otherwise (default or `-batch`) → **batch push mode**

## Step 5: Extract User Intent from Conversation

Before writing commit messages, review the recent conversation history (up to the last 100 user messages) to extract explicit instructions, requirements, or intent behind these code changes.

**What to look for:**
- Direct commands: "fix X", "add Y", "change Z to...", "optimize..."
- Repeated requests or clarifications across turns
- Specific values, thresholds, or configurations the user specified
- Bug descriptions, expected behaviors, or rejection reasons
- Feature names or module names the user explicitly mentioned

**How to apply:**
- Cross-reference user intent with the actual `git diff` content
- If user intent conflicts with diff inference, prioritize user intent
- Incorporate specific terms the user used into the commit message

## Step 6: Commit Each Group

### Pre-Flight Check (MANDATORY)

Before `git add`, verify every file path:

```bash
# Check files exist AND are inside the git repo
git ls-files --error-unmatch <file1> <file2> ... 2>&1
# OR
ls <file1> <file2> ... 2>&1
```

**If any file is missing or outside the repo:**
- Remove it from the group immediately
- If the group becomes empty, skip it
- Common causes: file is outside repo (`~/.claude/`, `/tmp/`), wrong path, wrong case (`skill.md` vs `SKILL.md`)
- Never blindly `git add` a path that doesn't exist — `git add` will error and the subsequent `git commit` will either fail or commit nothing

For each group, run:

```bash
git add <files_in_group>
git commit -m "<type>: <description>"
```

**If `git add` fails** (non-zero exit): stop, report the failing paths, do NOT proceed to commit.

### Commit Message Rules

| Scenario | Message Rule |
|----------|-------------|
| User provided message + single group | Use user's message as-is |
| User provided message + multiple groups | `"用户消息 — <子主题>"` |
| No user message | Auto-generate based on **both** file changes AND user intent from conversation history |

Auto-generate type from changes:
- `fix:` — bug fixes, null checks, error handling
- `feat:` — new features, new screens, new APIs
- `style:` — UI changes, text updates, colors, fonts
- `chore:` — config, tooling, dependencies, cleanup
- `refactor:` — restructuring without behavior change

**Intent-driven examples:**
- If user said "把这个按钮改大一点" + diff shows width/height change → `style: 增大跳过按钮尺寸`
- If user said "这里埋点重复上报了" + diff shows deduplication flags → `fix: 修复占卜流程退出埋点重复上报`
- If user said "抽牌页太灵敏了" + diff shows sensitivity constant change → `fix: 降低抽牌页卡片拖动灵敏度`

### Co-Authored-By

Always add to commit message:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

## Step 7: Pull Remote Changes Before Push

Before pushing, check if the remote has new commits:

```bash
git fetch origin <current-branch>
```

Compare local vs remote:
```bash
git rev-list --count HEAD..origin/<current-branch>
```

If remote has 0 new commits → skip to Step 8 (Push).

### If Remote Has New Commits

Show the user what changed remotely:
```
Remote has N new commit(s):
  <hash1> <message1>
  <hash2> <message2>
  ...

Pulling and merging...
```

Run merge:
```bash
git pull origin <current-branch>
```

### Merge Result

**No conflicts:**

Show a summary of the remote changes and proceed:
```
✅ Merge successful. Remote changes:
  file1  (+X lines)
  file2  (+Y lines)

Proceeding to push...
```

**Conflicts detected:**

Stop immediately and tell the user:
```
⚠️ Merge conflicts detected in:
  - <conflicting-file1>
  - <conflicting-file2>

Please resolve the conflicts manually, then re-run /gcp to continue.
```

Do NOT attempt to auto-resolve conflicts. Wait for the user to handle them.

## Step 8: Push

First, check if local is ahead of remote:
```bash
git rev-list --count origin/<current-branch>..HEAD
```

If 0 (nothing to push):
```
✅ Already up to date — nothing to push
```
Skip push entirely.

If local is ahead:

### Push with SSH → HTTPS Fallback

First, try normal push:
```bash
git push origin <current-branch>
```

**If push fails with SSH errors** (timeout, `broken pipe`, `Could not read from remote repository`):

1. Extract the HTTPS URL from the remote SSH URL:
   - `git@github.com:owner/repo.git` → `https://github.com/owner/repo.git`
   - Use `git remote get-url origin` to get the current URL

2. Check HTTPS connectivity before attempting fallback:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://github.com
   ```
   If returns 2xx → HTTPS reachable, proceed with fallback.

3. Retry push via HTTPS:
   ```bash
   git push https://github.com/owner/repo.git <current-branch>
   ```

4. If HTTPS push also fails → report error and stop.

**Do NOT** permanently change the remote URL — use the HTTPS URL inline so the SSH remote config is preserved.

### Batch Mode (default)

After all commits (and successful pull), execute push with SSH → HTTPS fallback as described above.

### Per-Commit Mode (-per)

After each individual commit (and successful pull before each push), execute push with SSH → HTTPS fallback as described above.

## Step 9: Report Result

**If commits were made:**
```
✅ Committed N groups:
  - <hash1> <message1>
  - <hash2> <message2>
  - [...]

✅ Pushed to <branch>
```

**If working tree was clean (no commits):**
```
✅ Working tree clean, no commits needed
[Followed by Step 8 push result]
```

## Safety Rules

- **Merge/rebase in progress?** Abort with warning
- **Push fails?** If SSH timeout → auto-fallback to HTTPS push. If HTTPS also fails → show error, suggest `git pull --rebase`
- **Never force push** (`--force` or `-f`)
- **Conflicts detected?** Stop and ask user to resolve, do NOT auto-resolve
