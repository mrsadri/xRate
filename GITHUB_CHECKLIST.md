# Pre-Push to GitHub Checklist ✅

Use this checklist before pushing your code to GitHub to ensure everything is secure and ready.

## Security Checks 🔒

- [ ] **No sensitive data in code**
  - [ ] No API keys, tokens, or passwords in source files
  - [ ] No `.env` file (should be in `.gitignore`)
  - [ ] No PEM files or SSH keys
  - [ ] No real server IPs (use placeholders in documentation)
  - [ ] No real bot tokens or channel IDs

- [ ] **Verify `.gitignore` is complete**
  - [ ] `.env` files excluded
  - [ ] `*.pem` and `*.key` files excluded
  - [ ] `data/*.json` (except samples) excluded
  - [ ] `*.log` files excluded
  - [ ] `__pycache__/` and `*.pyc` excluded
  - [ ] `.venv/` excluded

- [ ] **Check tracked files**
  ```bash
  git status
  git ls-files | grep -E "(\.env|\.pem|\.key|config\.json)"
  ```
  If any sensitive files appear, remove them and add to `.gitignore`

## Code Quality ✨

- [ ] **All tests pass**
  ```bash
  make test
  # or
  pytest
  ```

- [ ] **Linting passes**
  ```bash
  make lint
  # or
  ruff check .
  ```

- [ ] **No debug code left**
  - [ ] No `print()` statements (use logging)
  - [ ] No commented-out code blocks
  - [ ] No `TODO` comments with sensitive info

## Documentation 📚

- [ ] **README.md is up to date**
  - [ ] Installation instructions current
  - [ ] Configuration examples use placeholders
  - [ ] No real credentials in examples

- [ ] **DEPLOYMENT.md exists and is complete**
  - [ ] All placeholders used (no real IPs/PEMs)
  - [ ] Instructions are clear
  - [ ] Security best practices included

- [ ] **`.env.example` file exists**
  - [ ] All required variables documented
  - [ ] Example values are placeholders only
  - [ ] Comments explain each variable

## Repository Structure 🗂️

- [ ] **No old/unused files**
  - [ ] No duplicate files from old structure
  - [ ] No backup files (`.bak`, `.old`)
  - [ ] No temporary files

- [ ] **All necessary files present**
  - [ ] `README.md`
  - [ ] `DEPLOYMENT.md`
  - [ ] `.env.example`
  - [ ] `.gitignore`
  - [ ] `pyproject.toml`
  - [ ] `LICENSE` (if applicable)

## Final Verification 🔍

- [ ] **Review git diff**
  ```bash
  git diff
  git status
  ```
  Check for any accidental commits of sensitive data

- [ ] **Test clone in fresh directory** (optional but recommended)
  ```bash
  cd /tmp
  git clone /path/to/your/repo xrate-test
  cd xrate-test
  # Verify no sensitive files
  ```

## Quick Command Reference 🚀

```bash
# Check for secrets
grep -rE "(api[_-]?key|secret|token|password)" --include="*.py" --include="*.md" \
  | grep -v ".env.example" | grep -v ".git" | grep -v "your_" | grep -v "YOUR_"

# Check tracked files
git ls-files

# Verify .gitignore
git check-ignore -v .env data/*.json *.pem

# Run tests
make test

# Run linters
make lint

# Final status check
git status
```

## After Pushing 🎉

- [ ] Verify repository is public/private as intended
- [ ] Check GitHub Actions run successfully (if configured)
- [ ] Verify no sensitive data visible in GitHub's file viewer
- [ ] Test cloning the repository works

---

**Remember:** Once you push sensitive data to GitHub, it's in the history forever!
Always check twice before pushing! 🔒

