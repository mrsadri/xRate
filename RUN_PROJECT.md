# 🚀 How to Run XRate Project

## 📑 Table of Contents

1. [Method 1: Using Python Module (Recommended)](#method-1-using-python-module-recommended)
2. [Method 2: Using Run Script](#method-2-using-run-script)
3. [Method 3: Using Stop Script](#method-3-using-stop-script-easy-way-to-stop-bot)
4. [Method 4: Run in Background (Production)](#method-4-run-in-background-production)
5. [Required Environment Variables](#required-environment-variables)
6. [Troubleshooting](#troubleshooting)
   - [Error: "setup.py or setup.cfg not found"](#error-setuppy-or-setupcfg-not-found--editable-mode-requires-setuptools-based-build)
   - [Import Errors](#import-errors)
   - [Missing .env file](#missing-env-file)
   - [Stopping the Bot](#stopping-the-bot)
   - [Port Already in Use / Bot Already Running](#port-already-in-use--bot-already-running)
7. [Verify Installation](#verify-installation)
8. [Deploying to Server](#-deploying-to-server)
   - [Step 1: Transfer Changes to Server](#step-1-transfer-changes-to-server)
   - [Step 2: On Server - Update and Run New Version](#step-2-on-server---update-and-run-new-version)
   - [Quick Deployment Workflow](#quick-deployment-workflow)
   - [Important Notes](#important-notes)

---

## Method 1: Using Python Module (Recommended)

```bash
# 1. Navigate to project directory
cd /Users/masih/Downloads/xrate

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Upgrade pip and install build tools (required for editable install)
pip install --upgrade pip setuptools wheel

# 4. Install dependencies
pip install -e .

# 5. Run the bot
python -m xrate
```

## Method 2: Using Run Script

```bash
# Make script executable (first time only)
chmod +x scripts/run.sh

# Run the script
./scripts/run.sh
```

The script will:
- Automatically create virtual environment if needed
- Install dependencies
- Check for .env file
- Start the bot

## Method 3: Using Stop Script (Easy Way to Stop Bot)

```bash
# Make script executable (first time only)
chmod +x scripts/stop.sh

# Stop the bot
./scripts/stop.sh
```

The stop script will:
- Try to use PID file first (most reliable)
- Fall back to finding process by name
- Clean up stale PID files

## Method 4: Run in Background (Production)

```bash
# Run in background with logging
nohup python -m xrate > bot.log 2>&1 &

# View logs
tail -f bot.log

# Stop the bot (choose one method):

# Method 1: Using PID file (recommended)
if [ -f data/bot.pid ]; then
  kill $(cat data/bot.pid) && rm data/bot.pid
fi

# Method 2: Find and kill process
ps aux | grep -i "python.*xrate" | grep -v grep | awk '{print $2}' | xargs kill

# Method 3: Using pkill (may not work with all Python installations)
pkill -f "python.*xrate" || pkill -f "xrate"
```

## Required Environment Variables

Before running, make sure your `.env` file has:

```bash
# Required
BOT_TOKEN=your_telegram_bot_token
CHANNEL_ID=@your_channel
ADMIN_USERNAME=YourUsername

# Optional (for fallback)
NAVASAN_API_KEY=your_navasan_key

# Optional (for AI analysis)
AVALAI_KEY=your_avalai_key

# Optional (for test channel)
TEST_CHANNEL_ID=@your_test_channel
```

## Troubleshooting

### Error: "setup.py or setup.cfg not found" / "editable mode requires setuptools-based build"
```bash
# Solution: Upgrade pip and build tools first
pip install --upgrade pip setuptools wheel
# Then install the project
pip install -e .
```

### Import Errors
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
```

### Missing .env file
```bash
# Create your .env file with required configuration
# See .env.example for reference (if needed)
```

### Stopping the Bot

#### Method 1: Using PID File (Recommended)
```bash
# Check if PID file exists
if [ -f data/bot.pid ]; then
  kill $(cat data/bot.pid)
  rm data/bot.pid
  echo "Bot stopped"
else
  echo "No PID file found"
fi
```

#### Method 2: Find and Kill Process
```bash
# Find the process
ps aux | grep -i "python.*xrate" | grep -v grep

# Kill it (replace PID with actual process ID)
kill <PID>

# Or kill all matching processes
ps aux | grep -i "python.*xrate" | grep -v grep | awk '{print $2}' | xargs kill
```

#### Method 3: Using pkill (Alternative)
```bash
# More flexible pattern that works with different Python paths
pkill -f "python.*xrate" || pkill -f "xrate"
```

### Port Already in Use / Bot Already Running
```bash
# Check if bot is already running
ps aux | grep -i "python.*xrate" | grep -v grep

# If PID file exists, use it
if [ -f data/bot.pid ]; then
  kill $(cat data/bot.pid)
fi
```

## Verify Installation

```bash
# Check Python version (should be 3.9+)
python3 --version

# Check if package is installed
pip show xrate

# Test imports
python3 -c "from xrate.config import settings; print('✅ Setup OK')"
```

## 🚀 Deploying to Server

### Step 1: Transfer Changes to Server

#### Option A: Using Git (Recommended)
```bash
# On your local machine, commit and push changes
git add .
git commit -m "Update: description of changes"
git push origin main

# On server, pull the latest changes
cd /path/to/xrate
git pull origin main
```

#### Option B: Using rsync (Direct file transfer)
```bash
# From your local machine, sync files to server
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.git' --exclude 'data/*.json' --exclude 'bot.log' \
  ./ user@server:/path/to/xrate/
```

#### Option C: Using scp (Simple file copy)
```bash
# Copy entire project directory (excluding large files)
scp -r --exclude '.venv' --exclude '__pycache__' \
  ./ user@server:/path/to/xrate/
```

### Step 2: On Server - Update and Run New Version

```bash
# 1. Connect to server
ssh user@server

# 2. Navigate to project directory
cd /path/to/xrate

# 3. Stop the current running bot (if running)
./scripts/stop.sh
# OR manually:
if [ -f data/bot.pid ]; then
  kill $(cat data/bot.pid) && rm data/bot.pid
fi

# 4. Activate virtual environment (if using one)
source .venv/bin/activate

# 5. Update dependencies (if requirements changed)
pip install --upgrade pip setuptools wheel
pip install -e .

# 6. Verify your .env file is configured (don't overwrite it!)
# Your .env file should already be on the server with correct values

# 7. Run the new version

# Option A: Run in foreground (for testing)
python -m xrate

# Option B: Run in background (production)
nohup python -m xrate > bot.log 2>&1 &

# Option C: Run with run script
./scripts/run.sh

# 8. Check if bot started successfully
tail -f bot.log
# Or check process
ps aux | grep -i "python.*xrate" | grep -v grep
```

### Quick Deployment Workflow

```bash
# Complete workflow from local to server:

# 1. Local: Commit and push
git add .
git commit -m "Update: your changes"
git push origin main

# 2. Server: Deploy and restart
ssh user@server << 'EOF'
cd /path/to/xrate
git pull origin main
./scripts/stop.sh
source .venv/bin/activate 2>/dev/null || true
pip install --upgrade pip setuptools wheel
pip install -e .
nohup python -m xrate > bot.log 2>&1 &
tail -f bot.log
EOF
```

### Important Notes

⚠️ **Never overwrite your `.env` file on the server!**
- Keep your production `.env` file safe on the server
- Don't copy `.env.example` over your production `.env`
- Your `.env` file contains real API keys and should not be committed to git

✅ **Best Practices:**
- Always stop the bot before updating
- Test the new version briefly in foreground mode before running in background
- Keep backups of your `data/` directory (contains state and stats)
- Monitor logs after deployment: `tail -f bot.log`

