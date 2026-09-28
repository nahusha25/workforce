# Prompt 07 — Git Commit

Use this prompt to create proper atomic commits.

## Instructions

Follow `.ai/rules/git-rules.md`.

### Step 1 — Review Changes
```bash
git status
git diff --staged
git diff
```

### Step 2 — Group by Intent
Separate changes into logical groups:
- Feature code → `feat` commit
- Bug fix → `fix` commit
- Refactoring → `refactor` commit
- Test additions → `test` commit
- Documentation → `docs` commit

### Step 3 — Stage and Commit Each Group
```bash
git add <files-for-group-1>
git commit -m "<type>(<scope>): <description>"

git add <files-for-group-2>
git commit -m "<type>(<scope>): <description>"
```

### Step 4 — Verify
- [ ] Each commit has one logical intent
- [ ] Message follows Conventional Commits format
- [ ] No vague messages (update, changes, fix stuff, final, wip)
- [ ] Breaking changes are flagged with `!` and `BREAKING CHANGE:` footer
- [ ] No secrets in committed files
- [ ] Tests pass

### Format
```
<type>(<scope>): <description>

[optional body explaining WHY, not WHAT]

[optional footer]
```

### Examples
```
feat(employee): add employee registration API endpoint
fix(attendance): reject duplicate check-in for same date
test(verification): add supervisor approval E2E journey
docs(phase-0): update database architecture with indexes
refactor(daily-work): extract photo upload service
```
