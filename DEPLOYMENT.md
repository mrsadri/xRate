# XRate Bot - Complete Server Deployment Guide

> **Perfect for Beginners!** 📚  
> This guide is written for developers of all skill levels. Every command is explained in detail.  
> If you're new to servers, SSH, or systemd services - don't worry! We'll explain everything step by step.

---

## Table of Contents

1. [What is this guide?](#what-is-this-guide)
2. [Prerequisites - What you need](#prerequisites---what-you-need)
3. [Finding Your SSH Key (PEM File)](#finding-your-ssh-key-pem-file)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Managing Your Bot](#managing-your-bot)
6. [Troubleshooting](#troubleshooting)
7. [Understanding How Services Work](#understanding-how-services-work)
8. [Quick Reference Commands](#quick-reference-commands)

---

## What is this guide?

This document teaches you how to deploy (put on a server) the XRate Telegram bot so it runs 24/7 on a remote Ubuntu server.

**Think of it like this:**  
- Your Mac = your development computer (where you write code)
- The server = a computer that's always on the internet (where your bot lives)
- SSH = a secure way to connect and control the server from your Mac

The bot will run automatically, even when your Mac is turned off! ✨

---

## Prerequisites - What You Need

Before starting, make sure you have:

### 1. **Local Machine (Your Mac)**

- **Project Location**: `/Users/masih/Downloads/xrate`  
  *(This is where your project code lives on your computer)*
  
- **SSH Key File**: `~/.ssh/your-key-name.pem`  
  *(This is like a password file that lets you securely connect to your server - see [Finding Your SSH Key](#finding-your-ssh-key-pem-file) below)*
  
- **Environment File**: `.env` file with all API keys configured  
  *(This file contains secrets like your bot token and API keys - never share it!)*

### 2. **Remote Server (The Computer That Runs Your Bot)**

- **Operating System**: Ubuntu 24.04.3 LTS (or similar Linux server)  
  *(This is like Windows/Mac, but for servers)*
  
- **Python Version**: Python 3.12+ installed  
  *(The programming language your bot uses)*
  
- **Server IP Address**: `YOUR_SERVER_IP`  
  *(This is like a phone number for your server - replace with your actual IP)*
  
- **SSH Access**: Ability to connect with sudo privileges  
  *(SSH = Secure Shell, a way to control the server. Sudo = "super user do", lets you run admin commands)*

### 3. **How to Connect to Server**

**SSH Command** *(Replace placeholders with your actual values)*:
```bash
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ubuntu@YOUR_SERVER_IP
```

**What this command does:**
- `ssh` = the command to connect to a remote server
- `-i` = "identity file" (your key file)
- `~/.ssh/YOUR_KEY_NAME.pem` = path to your security key
- `ubuntu@YOUR_SERVER_IP` = username@server-address

**Example** *(with fake values)*:
```bash
ssh -i ~/.ssh/my-server-key.pem ubuntu@192.168.1.100
```

---

## Finding Your SSH Key (PEM File)

### What is a PEM file?

A PEM file (`.pem`) is your **private key** - like a secret password that lets you connect to your server securely. It's given to you when you set up your server (like on AWS, DigitalOcean, etc.).

### How to Find Your PEM File

#### Method 1: Check Common Location (Most Likely)

Most SSH keys are stored in the `~/.ssh/` folder. Try this:

```bash
# List all files in your SSH directory
ls -la ~/.ssh/

# Look for files ending in .pem
ls -la ~/.ssh/*.pem
```

**What you're looking for:**
- Files ending in `.pem` (like `mykey.pem`, `server.pem`)
- Files ending in `.key` (sometimes keys use this extension)
- Files with names like `id_rsa`, `id_ed25519` (common default names)

#### Method 2: Search Your Entire Computer

If you're not sure where it is, search everywhere:

```bash
# Search for .pem files (may take a minute)
find ~ -name "*.pem" -type f 2>/dev/null

# Search for .key files too
find ~ -name "*.key" -type f 2>/dev/null

# Search in Downloads folder (common place)
find ~/Downloads -name "*.pem" -type f 2>/dev/null
```

**What this does:**
- `find` = command to search for files
- `~` = your home directory (`/Users/your-username`)
- `-name "*.pem"` = look for files ending in .pem
- `-type f` = only files, not folders
- `2>/dev/null` = hide error messages

#### Method 3: Check Your Email/Downloads

When you first set up your server, the provider (AWS, DigitalOcean, etc.) usually:
- Emails you the key file
- Or lets you download it
- Check your Downloads folder: `~/Downloads/*.pem`

#### Method 4: Check Server Provider Documentation

If you created your server on:
- **AWS**: Check EC2 dashboard → Key Pairs
- **DigitalOcean**: Check API/Droplets → SSH Keys
- **Linode**: Check Account → API Keys
- **Other providers**: Check their documentation for "SSH keys" or "access keys"

### Understanding the File Path

Once you find your PEM file, note its **full path**:

**Examples:**
- `~/.ssh/mykey.pem` ← Most common location
- `~/Downloads/server-key.pem` ← If you downloaded it
- `/Users/yourname/Documents/key.pem` ← If you moved it

**The `~` symbol means:** "Your home directory"  
- On Mac: `/Users/your-username`
- On Linux: `/home/your-username`

**So `~/.ssh/key.pem` is the same as `/Users/your-username/.ssh/key.pem`**

### Setting Correct Permissions

For security, your PEM file must have specific permissions:

```bash
# Set correct permissions (replace with your actual file path)
chmod 400 ~/.ssh/YOUR_KEY_NAME.pem
```

**What this does:**
- `chmod` = "change mode" (set file permissions)
- `400` = only you can read it, no one can write/execute
- This is required for security - SSH won't work if permissions are wrong!

**Verify it worked:**
```bash
ls -la ~/.ssh/YOUR_KEY_NAME.pem
# Should show: -r-------- (read-only for owner)
```

---

## Step-by-Step Deployment

### Step 1: Test SSH Connection

**Purpose:** Make sure you can connect to your server before we start deploying.

**From your Mac, run:**

```bash
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ubuntu@YOUR_SERVER_IP 'uname -a && python3 --version'
```

**What this does:**
- Connects to your server
- Runs two commands: `uname -a` (shows system info) and `python3 --version` (shows Python version)
- Disconnects automatically after showing results

**Replace:**
- `YOUR_KEY_NAME.pem` with your actual PEM filename
- `YOUR_SERVER_IP` with your actual server IP address

**Expected output:**
```
Linux ubuntu-server 6.8.0-45-generic ... x86_64 GNU/Linux
Python 3.12.3
```

**If it works:** ✅ You're ready to proceed!  
**If it fails:** Check that your IP, username, and key file path are correct.

---

### Step 2: Transfer Project Files to Server

**Purpose:** Copy all your code from your Mac to the server so it can run there.

**From your Mac, navigate to your project folder:**

```bash
# Go to your project directory
cd /Users/masih/Downloads/xrate
```

**Then transfer files using rsync:**

```bash
rsync -avz --progress \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='bot.log' \
  --exclude='*.log' \
  --exclude='data/*.json' \
  --exclude='.env' \
  -e "ssh -i ~/.ssh/YOUR_KEY_NAME.pem" \
  ./ ubuntu@YOUR_SERVER_IP:/tmp/xrate/
```

**What this command does:**
- `rsync` = tool to copy files efficiently (faster than regular copy)
- `-avz` = options:
  - `a` = archive mode (preserves permissions, timestamps)
  - `v` = verbose (show what's happening)
  - `z` = compress during transfer (faster)
- `--progress` = show progress bar
- `--exclude='.git'` = don't copy the git folder (not needed on server)
- `--exclude='.venv'` = don't copy virtual environment (we'll create a new one)
- `--exclude='.env'` = **IMPORTANT:** Don't copy your secrets file yet (we'll do it securely later)
- `-e "ssh -i ..."` = use SSH with your key to connect
- `./` = copy from current directory (your Mac)
- `ubuntu@YOUR_SERVER_IP:/tmp/xrate/` = copy to `/tmp/xrate/` folder on server

**Expected result:**
- Files transferred to `/tmp/xrate/` on server
- You'll see a summary showing files sent/received
- No errors

**Why `/tmp/xrate/`?** It's a temporary location. Later, we'll move files to the permanent location `/opt/xrate/`.

---

### Step 3: Verify Files on Server

**Purpose:** Make sure all files arrived safely on the server.

**SSH to your server:**

```bash
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ubuntu@YOUR_SERVER_IP
```

**Once connected, check files:**

```bash
# Go to the folder we just copied files to
cd /tmp/xrate

# List all files (ls = list, -la = show details)
ls -la

# Check that important folders exist
ls -la deploy/      # Should show deployment scripts
ls -la src/xrate/   # Should show your Python code

# Verify Python version
python3 --version
```

**What each command does:**
- `cd /tmp/xrate` = "change directory" to the folder we copied files to
- `ls -la` = list all files with details (permissions, size, date)
- `ls -la deploy/` = check the deploy folder exists
- `ls -la src/xrate/` = check your source code exists
- `python3 --version` = confirm Python is installed (need 3.12+)

**Expected result:**
- ✅ All project files present
- ✅ `deploy/` directory exists (contains deployment scripts)
- ✅ `src/xrate/` directory exists (contains your bot code)
- ✅ Python 3.12.3 (or similar) confirmed

**If something is missing:** Re-run Step 2.

---

### Step 4: Run Automated Deployment Script

**Purpose:** This script automatically sets up everything on the server (creates user, installs dependencies, etc.).

**On the server (you should already be SSH'd in from Step 3):**

```bash
# Make sure we're in the right folder
cd /tmp/xrate

# Make the script executable (allow it to run)
chmod +x deploy/deploy.sh

# Run the deployment script with systemd option
sudo ./deploy/deploy.sh systemd
```

**What this script does automatically:**
1. ✅ Creates a service user called "xrate" (for security - bot runs as this user, not root)
2. ✅ Copies files to `/opt/xrate` (permanent location)
3. ✅ Creates a Python virtual environment (isolated Python environment)
4. ✅ Installs all dependencies (Python packages your bot needs)
5. ✅ Configures systemd service (so bot can run as a background service)

**What is `sudo`?**  
"Super User Do" - runs the command as administrator. Needed to create users and install system-wide.

**What is `systemd`?**  
The system service manager on Linux - it keeps your bot running even if you disconnect or reboot the server.

**Expected result:**
- Script runs without errors
- Dependencies installed successfully
- Service user "xrate" created
- Files copied to `/opt/xrate`

#### ⚠️ If Installation Fails (Egg-Info Error)

Sometimes you might see an error like:
```
ERROR: Failed to build 'file:///opt/xrate'
Cannot update time stamp of directory 'src/xrate.egg-info'
```

**Fix it:**

```bash
# Remove the problematic directory
sudo rm -rf /opt/xrate/src/xrate.egg-info

# Fix ownership (make sure xrate user owns everything)
sudo chown -R xrate:xrate /opt/xrate

# Retry installation as the xrate user
sudo -u xrate bash -c "cd /opt/xrate && .venv/bin/pip install -e '.[dev]'"
```

**What these commands do:**
- `rm -rf` = remove folder and all contents
- `chown -R` = change ownership of all files/folders
- `sudo -u xrate` = run command as the xrate user (not root, which is safer)
- `pip install -e '.[dev]'` = install project in "editable" mode with dev dependencies

---

### Step 5: Complete Systemd Service Setup

**Purpose:** Configure the service so systemd can manage your bot (start, stop, restart automatically).

**On the server:**

```bash
# Go to the project folder
cd /opt/xrate

# Copy the service file to systemd directory
sudo cp deploy/xrate.service /etc/systemd/system/xrate.service

# Tell systemd to reload its configuration
sudo systemctl daemon-reload

# Enable the service (make it start automatically on boot)
sudo systemctl enable xrate
```

**What each command does:**
- `cp` = copy file
- `/etc/systemd/system/` = where systemd service files live
- `daemon-reload` = refresh systemd so it knows about new services
- `enable` = make service start automatically when server boots

**Verify it worked:**

```bash
# View the service file to make sure it copied correctly
sudo cat /etc/systemd/system/xrate.service | head -20
```

**Expected result:**
- ✅ Service file copied successfully
- ✅ Service enabled (will start on boot)
- ✅ Service file shows correct paths

---

### Step 6: Create .env Configuration File

**Purpose:** Add your secret configuration (bot token, API keys) to the server.

**⚠️ IMPORTANT:** We do this separately for security - never copy `.env` files in regular file transfers!

**From your Mac (in a NEW terminal, not the SSH session):**

```bash
# Make sure you're in your project folder
cd /Users/masih/Downloads/xrate

# Copy .env file to server's /tmp folder (temporary)
scp -i ~/.ssh/YOUR_KEY_NAME.pem \
    /Users/masih/Downloads/xrate/.env \
    ubuntu@YOUR_SERVER_IP:/tmp/xrate.env
```

**What `scp` does:**
- "Secure Copy" - copies files over SSH securely
- `-i` = identity file (your PEM key)
- Last two arguments = source file and destination

**Then on the server (SSH back in if you disconnected):**

```bash
# Move the file to the permanent location
sudo mv /tmp/xrate.env /opt/xrate/.env

# Set correct ownership (xrate user should own it)
sudo chown xrate:xrate /opt/xrate/.env

# Set secure permissions (only owner can read/write)
sudo chmod 600 /opt/xrate/.env

# Verify it worked
ls -la /opt/xrate/.env
```

**What these commands do:**
- `mv` = move file (from /tmp to /opt/xrate)
- `chown` = change owner to xrate user (not root - more secure)
- `chmod 600` = only owner can read/write, no one else (security!)

**Expected result:**
- File permissions: `-rw-------` (600 = read/write for owner only)
- Owner: `xrate:xrate`
- File exists at `/opt/xrate/.env`

**Security Note:** The `.env` file contains secrets. That's why we:
1. Set permissions to 600 (only owner can access)
2. Own it by xrate user (not root)
3. Never commit it to git
4. Copy it separately with scp (encrypted transfer)

---

### Step 7: Start the Service

**Purpose:** Actually start your bot running on the server!

**On the server:**

```bash
# Start the service
sudo systemctl start xrate

# Check if it started successfully
sudo systemctl status xrate

# View recent logs to see if there are any errors
sudo journalctl -u xrate -n 100 --no-pager
```

**What each command does:**
- `start` = tell systemd to start the service
- `status` = check if service is running (should show "active (running)")
- `journalctl -u xrate` = view logs for the xrate service
- `-n 100` = show last 100 log lines
- `--no-pager` = don't use pagination (show all at once)

**Expected result:**
- ✅ Status: `active (running)`
- ✅ Logs show: `"Starting bot polling… post interval=15 minutes"`
- ✅ No critical errors
- ✅ Regular `getUpdates` calls (every ~10 seconds - this is normal!)

**What are "getUpdates calls"?**  
The bot checks Telegram for new messages every ~10 seconds. This is separate from the market update schedule (every 15 minutes). It's normal and necessary!

---

### Step 8: Final Verification

**Purpose:** Make sure everything works from the user's perspective!

#### Test 1: From Telegram

1. Open Telegram on your phone/computer
2. Find your bot (search for it)
3. Send the command: `/start`
4. **Expected:** You should receive a message with current market rates

#### Test 2: Admin Command (If You're Admin)

1. Send: `/post`
2. **Expected:** 
   - Bot posts to your channel
   - Registers you as admin (if first time)
   - Shows confirmation message

#### Test 3: Service Status

**On server:**
```bash
sudo systemctl status xrate
```

**Expected:** Should show `active (running)`

---

## Managing Your Bot

### Service Management Commands

**Start the Bot:**
```bash
sudo systemctl start xrate
```
*Starts the bot service (if it's stopped)*

**Stop the Bot:**
```bash
sudo systemctl stop xrate
```
*Stops the bot (bot will no longer respond)*

**Restart the Bot:**
```bash
sudo systemctl restart xrate
```
*Stops and starts again (useful after updating code or config)*

**Check Status:**
```bash
sudo systemctl status xrate
```
*Shows if bot is running, memory usage, recent logs*

**View Logs (Live):**
```bash
sudo journalctl -u xrate -f
```
*Shows logs in real-time (press Ctrl+C to exit)*
- `-f` = "follow" (keep showing new log entries)

**View Last 100 Log Lines:**
```bash
sudo journalctl -u xrate -n 100
```

**View Logs Since Today:**
```bash
sudo journalctl -u xrate --since today
```

**View Only Error Logs:**
```bash
sudo journalctl -u xrate -p err
```
*`-p err` = priority error (only show errors)*

**Disable Auto-Start (On Boot):**
```bash
sudo systemctl disable xrate
```
*Bot won't start automatically when server reboots*

**Enable Auto-Start (On Boot):**
```bash
sudo systemctl enable xrate
```
*Bot will start automatically when server reboots (recommended)*

---

## Understanding How Services Work

### Will Closing My SSH Terminal Stop the Bot?

**NO!** 🎉

The bot runs as a **systemd service**, which means:
- ✅ It runs in the background, **independent of your SSH session**
- ✅ Closing your terminal will **NOT** stop the bot
- ✅ The bot will continue running even if you disconnect
- ✅ The bot will automatically restart on server reboot
- ✅ The bot will auto-restart if it crashes

**Think of it like this:**
- Your SSH session = a remote control
- The systemd service = the actual TV
- Disconnecting the remote control doesn't turn off the TV!

**To verify the bot is still running after closing terminal:**

```bash
# SSH back into server
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ubuntu@YOUR_SERVER_IP

# Check status
sudo systemctl status xrate
```

Should show: `active (running)` ✅

---

### How to Check If Only One Instance is Running

Sometimes multiple bot instances can cause problems. Here's how to check:

#### Method 1: Check systemd Service Status (Recommended) ⭐

```bash
sudo systemctl status xrate
```

**Look for:**
- `active (running)` status
- **ONE** `Main PID` line
- Should show only one process

**If you see multiple PIDs or "active (exited)"**, there might be an issue.

#### Method 2: Check PID File

```bash
# View the PID (Process ID) stored in file
cat /opt/xrate/data/bot.pid

# Verify that process is actually running
ps aux | grep $(cat /opt/xrate/data/bot.pid)
```

**What this does:**
- `cat` = display file contents (shows the process ID)
- `ps aux | grep` = list all processes and filter for that PID
- Should show only **one** matching process

#### Method 3: Count All Python Processes with xrate

```bash
ps aux | grep "python.*xrate" | grep -v grep
```

**What this does:**
- Lists all processes containing "python" and "xrate"
- `grep -v grep` = exclude the grep command itself from results
- Should show only **ONE** process

#### Method 4: Check Process by Service PID

```bash
# Get the PID from systemd
sudo systemctl status xrate | grep "Main PID"

# Then verify that process exists
ps -p <PID>
```

Replace `<PID>` with the number from the previous command.

#### Method 5: Verify PID File Matches Running Process

```bash
# Get PID from file
PID=$(cat /opt/xrate/data/bot.pid 2>/dev/null)

# Check if process exists
if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Bot is running (PID: $PID)"
else
    echo "❌ Bot is NOT running (stale PID file)"
fi
```

**What this does:**
- Reads PID from file
- Checks if that process ID actually exists
- Reports if bot is running or if PID file is outdated

#### Method 6: Quick Check Script

We've included a script in `scripts/check_instance.sh` that does all checks automatically!

**Copy it to server:**
```bash
# From your Mac
scp -i ~/.ssh/YOUR_KEY_NAME.pem \
    scripts/check_instance.sh \
    ubuntu@YOUR_SERVER_IP:/tmp/

# On server
sudo mv /tmp/check_instance.sh /opt/xrate/
sudo chmod +x /opt/xrate/check_instance.sh
sudo /opt/xrate/check_instance.sh
```

**Expected Result:**
```
✅ Bot running (PID: xxxxx)
   Process count: 1
```

**If you see process count > 1, fix it:**

```bash
# Stop all instances
sudo systemctl stop xrate
pkill -f "python.*xrate"

# Wait a moment
sleep 2

# Start service properly
sudo systemctl start xrate
```

---

## Troubleshooting

### Problem: Service Won't Start

**Symptoms:** `sudo systemctl start xrate` fails or service shows as "failed"

**Solution:**

```bash
# 1. Check logs for errors
sudo journalctl -u xrate -n 50

# 2. Verify .env file exists
ls -la /opt/xrate/.env

# 3. Check file permissions
sudo chown xrate:xrate /opt/xrate/.env
sudo chmod 600 /opt/xrate/.env

# 4. Try starting again
sudo systemctl restart xrate
```

**Common causes:**
- Missing `.env` file
- Wrong file permissions
- Missing dependencies
- Invalid configuration

---

### Problem: Service Starts But Bot Doesn't Respond

**Symptoms:** Service shows "active (running)" but Telegram bot doesn't respond to commands

**Solution:**

```bash
# 1. Check if bot is actually running
sudo systemctl status xrate

# 2. Verify .env has correct BOT_TOKEN
sudo -u xrate cat /opt/xrate/.env | grep BOT_TOKEN

# 3. Check recent logs for errors
sudo journalctl -u xrate -n 50

# 4. Test Telegram API connectivity
curl -I https://api.telegram.org
```

**Common causes:**
- Wrong `BOT_TOKEN` in `.env`
- Network issues (server can't reach Telegram API)
- Bot token revoked/expired

---

### Problem: Permission Denied Errors

**Symptoms:** Logs show "Permission denied" errors

**Solution:**

```bash
# Fix ownership of all files
sudo chown -R xrate:xrate /opt/xrate

# Fix .env permissions specifically
sudo chmod 600 /opt/xrate/.env
sudo chown xrate:xrate /opt/xrate/.env
```

**What this does:**
- Makes xrate user own all files (so bot can read/write)
- Sets secure permissions on .env file

---

### Problem: Bot Crashes/Restarts Repeatedly

**Symptoms:** Service keeps restarting, logs show errors repeatedly

**Solution:**

```bash
# 1. Check logs for error patterns
sudo journalctl -u xrate -n 200 | grep -i error

# 2. Verify all API keys in .env are correct
sudo -u xrate cat /opt/xrate/.env

# 3. Check if multiple instances running (might cause conflicts)
ps aux | grep xrate

# 4. Check system resources (maybe server is out of memory)
free -h
df -h
```

**Common causes:**
- Invalid API keys
- Network connectivity issues
- Multiple bot instances (conflict)
- Server out of resources (memory/disk)

---

### Problem: Cannot Connect to Telegram API

**Symptoms:** Logs show timeout errors connecting to `api.telegram.org`

**Solution:**

```bash
# 1. Test network connectivity
curl -I https://api.telegram.org

# 2. Verify BOT_TOKEN is correct
sudo -u xrate cat /opt/xrate/.env | grep BOT_TOKEN

# 3. Check firewall rules (bot needs outbound HTTPS)
# If using ufw:
sudo ufw status

# 4. Test DNS resolution
nslookup api.telegram.org
```

**Common causes:**
- Server firewall blocking outbound HTTPS
- Network outage
- DNS issues
- Incorrect bot token

---

## Quick Reference Commands

### Most Common Commands

```bash
# Start bot
sudo systemctl start xrate

# Stop bot
sudo systemctl stop xrate

# Restart bot
sudo systemctl restart xrate

# Check status
sudo systemctl status xrate

# View logs (live)
sudo journalctl -u xrate -f

# View last errors
sudo journalctl -u xrate -p err -n 20
```

### Connecting to Server

```bash
# Connect via SSH
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ubuntu@YOUR_SERVER_IP

# Run command on server without staying connected
ssh -i ~/.ssh/YOUR_KEY_NAME.pem ubuntu@YOUR_SERVER_IP 'command'
```

### File Locations

| Item | Location |
|------|----------|
| Installation Directory | `/opt/xrate` |
| Service File | `/etc/systemd/system/xrate.service` |
| Configuration File | `/opt/xrate/.env` |
| Logs (systemd) | `sudo journalctl -u xrate` |
| Logs (file, if enabled) | `/opt/xrate/logs/xrate.log` |
| Data Files | `/opt/xrate/data/` |
| Virtual Environment | `/opt/xrate/.venv` |
| Source Code | `/opt/xrate/src/xrate/` |

---

## File Locations Reference

### Installation Directory
```
/opt/xrate
```
*Main folder where bot lives*

### Service File
```
/etc/systemd/system/xrate.service
```
*Configuration file that tells systemd how to run your bot*

### Configuration File
```
/opt/xrate/.env
```
*Contains your secrets (bot token, API keys) - **NEVER SHARE THIS!***

### Logs

**Systemd Logs** (always available):
```bash
sudo journalctl -u xrate
```

**File Logs** (if file logging enabled in .env):
```
/opt/xrate/logs/xrate.log
```

### Data Files
```
/opt/xrate/data/
├── last_state.json      # Last posted market rates
├── stats.json           # Bot statistics
├── admin_store.json     # Admin user IDs
├── language.json        # Language preferences
└── bot.pid              # Process ID (prevents multiple instances)
```

### Virtual Environment
```
/opt/xrate/.venv
```
*Contains Python packages (dependencies)*

### Source Code
```
/opt/xrate/src/xrate/
```
*Your actual bot code*

---

## Environment Variables (.env file)

### Required Variables

```bash
BOT_TOKEN=your_bot_token_here          # From @BotFather on Telegram
CHANNEL_ID=@yourchannel                 # Your Telegram channel username
TEST_CHANNEL_ID=@yourtestchannel       # Optional: Test channel for /posttest
ADMIN_USERNAME=MasihSadri              # Admin username (without @)
NAVASAN_API_KEY=your_navasan_key        # Optional: From navasan.tech (fallback when crawlers fail)
AVALAI_KEY=your_avalai_key             # Optional: For AI market analysis
```

### Optional Variables (for server deployment)

```bash
# Logging Configuration
LOG_DIR=/opt/xrate/logs                # Directory for log files
XRATE_LOG_STDOUT=false                  # Disable stdout (for systemd)
LOG_MAX_BYTES=10485760                  # 10MB per log file
LOG_BACKUP_COUNT=5                      # Number of backup logs

# Custom PID file location (optional)
XRATE_PID_FILE=/opt/xrate/data/bot.pid
```

**For complete list of all variables, see `.env.example` file.**

---

## Security Notes

### 1. .env File Permissions

**Always:**
- ✅ Set permissions to `600` (read/write for owner only)
- ✅ Owner should be `xrate:xrate` (not root)
- ✅ Never commit to git (it's in `.gitignore`)

```bash
sudo chmod 600 /opt/xrate/.env
sudo chown xrate:xrate /opt/xrate/.env
```

### 2. Service Runs as Dedicated User

- ✅ User: `xrate` (not root - more secure)
- ✅ Limited permissions (can't access system files)
- ✅ Can only write to `/opt/xrate/data/`

### 3. File Ownership

- ✅ All files in `/opt/xrate` owned by `xrate:xrate`
- ✅ Service cannot write outside `/opt/xrate/data`

### 4. Network Security

- ✅ Bot only needs **outbound HTTPS** (no inbound ports)
- ✅ No need to open firewall ports
- ✅ Connections to:
  - `api.telegram.org`
  - `www.bonbast.com` (web crawler)
  - `alanchand.com` (web crawler)
  - `api.navasan.tech` (optional, fallback)
  - `api.wallex.ir` (optional, for Tether)
  - `api.avalai.ir` (optional, if using Avalai)

---

## Monitoring

### Real-time Log Monitoring

```bash
sudo journalctl -u xrate -f
```
*Shows logs as they happen (press Ctrl+C to exit)*

### Check Service Health

```bash
sudo systemctl status xrate
```
*Shows status, memory usage, recent activity*

### View Recent Errors

```bash
sudo journalctl -u xrate -p err -n 50
```
*Shows last 50 error-level log entries*

### View All Logs Since Boot

```bash
sudo journalctl -u xrate --since boot
```

### View Logs for Specific Date

```bash
sudo journalctl -u xrate --since "2025-11-01" --until "2025-11-02"
```

### Check Bot Process

```bash
ps aux | grep xrate
```
*Shows running bot process(es)*

### Check Resource Usage

```bash
sudo systemctl status xrate
```
*Shows Memory and CPU usage in the status output*

---

## Updating the Bot

When you make changes to your code, here's how to update:

### Step 1: Stop the Service

```bash
sudo systemctl stop xrate
```
*Stops bot so we can update files*

### Step 2: Backup Data

```bash
sudo -u xrate cp -r /opt/xrate/data /opt/xrate/data.backup
```
*Creates backup in case something goes wrong*

### Step 3: Transfer New Files

**From your Mac:**
```bash
cd /Users/masih/Downloads/xrate

rsync -avz --progress \
  --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.pytest_cache' --exclude='bot.log' \
  --exclude='*.log' --exclude='data/*.json' --exclude='.env' \
  -e "ssh -i ~/.ssh/YOUR_KEY_NAME.pem" \
  ./ ubuntu@YOUR_SERVER_IP:/tmp/xrate-update/
```

**On server:**
```bash
sudo rsync -av --exclude='.env' --exclude='data' \
    /tmp/xrate-update/ /opt/xrate/
sudo chown -R xrate:xrate /opt/xrate
```
*Copies new files while preserving .env and data*

### Step 4: Update Dependencies (If Needed)

```bash
sudo -u xrate bash -c "cd /opt/xrate && .venv/bin/pip install -e '.[dev]'"
```
*Only needed if you added new Python packages*

### Step 5: Restart Service

```bash
sudo systemctl start xrate
```

### Step 6: Verify

```bash
sudo systemctl status xrate
sudo journalctl -u xrate -n 50
```
*Check that everything works*

---

## Deployment Summary

Here's what we accomplished:

1. ✅ Verified SSH connection to server
2. ✅ Transferred project files to `/tmp/xrate/`
3. ✅ Verified files on server
4. ✅ Ran deployment script (systemd)
5. ✅ Created service user "xrate"
6. ✅ Installed dependencies in virtual environment
7. ✅ Configured systemd service
8. ✅ Copied .env file with API keys (securely)
9. ✅ Started service
10. ✅ Verified bot is running and responding

**Your bot is now:**
- Running 24/7 on the server
- Independent of your SSH session
- Auto-restarting on crashes
- Auto-starting on server reboot

**Key Locations:**
- **Bot Location**: `/opt/xrate`
- **Service Name**: `xrate`
- **Service User**: `xrate`
- **Logs**: `sudo journalctl -u xrate`

---

## Support & Additional Resources

### If You Have Issues

1. **Check logs:** `sudo journalctl -u xrate -n 100`
2. **Check status:** `sudo systemctl status xrate`
3. **Verify .env:** `sudo -u xrate cat /opt/xrate/.env`
4. **Review this deployment guide:** `DEPLOYMENT.md`
5. **Check deployment guide:** `deploy/SERVER_DEPLOYMENT.md`
6. **Check main README:** `README.md`

### Additional Documentation

- **📘 [Server Deployment Guide](deploy/SERVER_DEPLOYMENT.md)** - Detailed deployment instructions
- **📘 [README.md](README.md)** - Project documentation and features
- **📘 [Deploy README](deploy/README.md)** - Deployment overview

---

## Glossary (For Beginners)

**SSH (Secure Shell)**: A secure way to connect to and control a remote server over the internet.

**PEM File**: A private key file (`.pem`) used to authenticate with your server securely.

**systemd**: The service manager on Linux systems that controls background processes.

**Service**: A program that runs in the background, managed by systemd.

**Virtual Environment (venv)**: An isolated Python environment that contains only the packages your project needs.

**PID (Process ID)**: A unique number assigned to each running process.

**sudo**: "Super User Do" - runs a command as administrator (root user).

**rsync**: A tool for efficiently copying files between computers.

**scp**: "Secure Copy" - copies files securely over SSH.

**journalctl**: Command to view systemd service logs.

---

---

**Last Updated:** November 2, 2025

**Written for:** Developers of all skill levels, especially beginners! 🚀

---

