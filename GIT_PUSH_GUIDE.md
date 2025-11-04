# Git Push Guide - How to Push to GitHub

## Quick Commands

```bash
# 1. Add all changes (modified and new files)
git add .

# 2. Commit with a descriptive message
git commit -m "Add web crawlers, fix bugs, improve documentation

- Added Bonbast and AlanChand web crawlers for price fetching
- Integrated crawlers into posting logic (crawlers first, APIs fallback)
- Fixed 6 bugs including missing variable, duplicate imports, etc.
- Added comprehensive documentation and import comments to all files
- Created learning guide for Python beginners
- Updated test files with proper documentation
- Improved code modularity and DRY principles"

# 3. Push to GitHub
git push origin main
```

## Step-by-Step Instructions

### Step 1: Check What Will Be Committed
```bash
git status
```

This shows you all modified and new files.

### Step 2: Add Files to Staging
```bash
# Add all changes (recommended)
git add .

# OR add specific files
git add src/xrate/adapters/crawlers/
git add src/xrate/application/crawler_service.py
git add README.md
# ... etc
```

### Step 3: Commit Changes
```bash
# Commit with a message
git commit -m "Your commit message here"

# OR commit with a detailed multi-line message
git commit -m "Add web crawlers and fix bugs

- Added crawler integration
- Fixed bugs
- Updated documentation"
```

### Step 4: Push to GitHub
```bash
# Push to main branch
git push origin main

# If this is your first push or branch doesn't exist on remote:
git push -u origin main
```

## Complete Command Sequence

```bash
# Navigate to project directory (if not already there)
cd /Users/masih/Downloads/xrate

# Check current status
git status

# Add all changes
git add .

# Commit with descriptive message
git commit -m "Add web crawlers, fix bugs, improve documentation

Features:
- Web crawlers (Bonbast, AlanChand) for direct price fetching
- Crawlers integrated into posting logic with API fallback
- Comprehensive documentation and import comments

Bug Fixes:
- Fixed missing 'now' variable in post_rate_job
- Removed duplicate asyncio imports
- Fixed crawler integration issues
- Consolidated duplicate code

Documentation:
- Added module docstrings to all files
- Added import comments explaining each import
- Created learn_python_by_this_code.md guide
- Updated test files with proper documentation"

# Push to GitHub
git push origin main
```

## Alternative: Using Git Add Interactive

If you want to selectively add files:

```bash
# Interactive staging
git add -i

# Or add specific patterns
git add src/xrate/adapters/crawlers/*.py
git add docs/*.md
git add tests/*.py
```

## If You Get Authentication Errors

If you see authentication errors, you may need to:

1. **Use SSH instead of HTTPS:**
```bash
# Check current remote
git remote -v

# Change to SSH (if using HTTPS)
git remote set-url origin git@github.com:mrsadri/xRate.git

# Then push
git push origin main
```

2. **Or use Personal Access Token:**
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Create a token with `repo` permissions
   - Use token as password when pushing

## Verify Your Push

After pushing, verify on GitHub:

```bash
# Check remote status
git status

# View commit history
git log --oneline -5
```

## Common Issues

### Issue: "Your branch is ahead of 'origin/main'"
**Solution:** Just push normally - `git push origin main`

### Issue: "Authentication failed"
**Solution:** 
- Use SSH keys, or
- Use Personal Access Token, or
- Configure Git credentials: `git config --global credential.helper store`

### Issue: "Merge conflicts"
**Solution:**
```bash
# Pull latest changes first
git pull origin main

# Resolve conflicts, then:
git add .
git commit -m "Resolve merge conflicts"
git push origin main
```

---

**Ready to push?** Run these commands in order:

```bash
git add .
git commit -m "Add web crawlers, fix bugs, improve documentation"
git push origin main
```


