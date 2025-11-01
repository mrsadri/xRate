# 🚀 Server Deployment Guide

This guide explains how to deploy the XRate Telegram bot on a remote Linux server.

## 📋 Prerequisites

- **Linux server** (Ubuntu/Debian/CentOS/RHEL recommended)
- **Python 3.9+** installed
- **sudo/root access** for installation
- **SSH access** to the server

## 🎯 Deployment Options

The bot can be deployed using either:

1. **systemd** (recommended for modern Linux systems)
2. **Supervisor** (alternative process manager)

## 📦 Quick Deployment

### Option 1: Using the Deployment Script (Recommended)

1. **Transfer project to server:**
   ```bash
   # From your local machine
   rsync -av --exclude='.git' --exclude='.venv' ./ user@server:/tmp/xrate
   ```

2. **SSH to server and run deployment:**
   ```bash
   ssh user@server
   cd /tmp/xrate
   sudo ./deploy/deploy.sh systemd
   # or for supervisor:
   # sudo ./deploy/deploy.sh supervisor
   ```

3. **Configure environment:**
   ```bash
   sudo -u xrate nano /opt/xrate/.env
   # Add your BOT_TOKEN, API keys, etc.
   ```

4. **Start the service:**
   ```bash
   # For systemd:
   sudo systemctl start xrate
   
   # For supervisor:
   sudo supervisorctl start xrate
   ```

### Option 2: Manual Installation

#### Step 1: Create Service User

```bash
sudo useradd -r -s /bin/bash -d /opt/xrate xrate
```

#### Step 2: Install Project Files

```bash
sudo mkdir -p /opt/xrate
sudo chown xrate:xrate /opt/xrate

# Copy project files (exclude .git, .venv, etc.)
sudo rsync -av --exclude='.git' --exclude='.venv' \
    ./ /opt/xrate/

sudo chown -R xrate:xrate /opt/xrate
```

#### Step 3: Set Up Python Environment

```bash
cd /opt/xrate
sudo -u xrate python3 -m venv .venv
sudo -u xrate .venv/bin/pip install --upgrade pip setuptools wheel
sudo -u xrate .venv/bin/pip install -e ".[dev]"
```

#### Step 4: Configure Environment

```bash
sudo -u xrate cp .env.example .env
sudo -u xrate nano .env  # Edit with your API keys
```

#### Step 5: Install Service

**For systemd:**

```bash
# Copy and customize service file
sudo cp /opt/xrate/deploy/xrate.service /etc/systemd/system/xrate.service
sudo nano /etc/systemd/system/xrate.service  # Update paths if needed

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable xrate
sudo systemctl start xrate
```

**For supervisor:**

```bash
# Copy and customize config
sudo cp /opt/xrate/deploy/supervisor-xrate.conf /etc/supervisor/conf.d/xrate.conf
sudo nano /etc/supervisor/conf.d/xrate.conf  # Update paths if needed

# Reload and start
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start xrate
```

## 🔧 Service Management

### systemd Commands

```bash
# Start/Stop/Restart
sudo systemctl start xrate
sudo systemctl stop xrate
sudo systemctl restart xrate

# Status
sudo systemctl status xrate

# Enable/Disable auto-start
sudo systemctl enable xrate
sudo systemctl disable xrate

# View logs
sudo journalctl -u xrate -f          # Follow logs
sudo journalctl -u xrate -n 100      # Last 100 lines
sudo journalctl -u xrate --since today  # Since today
```

### Supervisor Commands

```bash
# Start/Stop/Restart
sudo supervisorctl start xrate
sudo supervisorctl stop xrate
sudo supervisorctl restart xrate

# Status
sudo supervisorctl status xrate

# View logs
tail -f /opt/xrate/logs/xrate.log
tail -f /opt/xrate/logs/xrate_error.log
```

## 📝 Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Telegram Configuration
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@yourchannel
ADMIN_USERNAME=YourUsername

# API Keys
FASTFOREX_KEY=your_key
NAVASAN_API_KEY=your_key
BRSAPI_KEY=your_key
AVALAI_KEY=your_key  # Optional

# Logging (optional, for file-based logging)
LOG_DIR=/opt/xrate/logs
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
XRATE_LOG_STDOUT=false  # Disable stdout when using systemd/supervisor
```

### Logging Configuration

The bot supports multiple logging configurations:

1. **Default (stdout only)** - Good for development
2. **File-based logging** - Set `LOG_DIR` or `LOG_FILE` in `.env`
3. **Both stdout and file** - Useful for debugging

**Example `.env` entries:**

```bash
# File-based logging (recommended for servers)
LOG_DIR=/opt/xrate/logs
XRATE_LOG_STDOUT=false

# Or specify exact log file
LOG_FILE=/var/log/xrate/bot.log
```

Log files automatically rotate when they reach the size limit.

## 🔍 Troubleshooting

### Check if service is running

```bash
# systemd
sudo systemctl status xrate

# supervisor
sudo supervisorctl status xrate

# Or check process
ps aux | grep xrate
```

### View recent logs

```bash
# systemd
sudo journalctl -u xrate -n 50

# supervisor
tail -n 50 /opt/xrate/logs/xrate.log
```

### Check for errors

```bash
# systemd
sudo journalctl -u xrate -p err

# supervisor
grep -i error /opt/xrate/logs/xrate_error.log
```

### Common Issues

**1. Service won't start:**
- Check `.env` file exists and is readable
- Verify Python virtual environment is set up
- Check service logs for specific errors

**2. Permission errors:**
- Ensure files are owned by `xrate` user:
  ```bash
  sudo chown -R xrate:xrate /opt/xrate
  ```

**3. Multiple instances running:**
- Check PID file: `cat /opt/xrate/data/bot.pid`
- Kill old processes: `pkill -f 'python.*xrate'`

**4. Bot not responding:**
- Check Telegram API connectivity
- Verify `BOT_TOKEN` is correct
- Check network/firewall settings

## 🔄 Updating the Bot

1. **Stop the service:**
   ```bash
   sudo systemctl stop xrate  # or supervisorctl stop xrate
   ```

2. **Backup data:**
   ```bash
   sudo -u xrate cp -r /opt/xrate/data /opt/xrate/data.backup
   ```

3. **Update code:**
   ```bash
   cd /opt/xrate
   # Pull updates or copy new files
   sudo -u xrate git pull  # if using git
   # OR copy new files manually
   
   # Update dependencies
   sudo -u xrate .venv/bin/pip install -e ".[dev]"
   ```

4. **Restart service:**
   ```bash
   sudo systemctl start xrate  # or supervisorctl start xrate
   ```

## 🛡️ Security Best Practices

1. **File Permissions:**
   ```bash
   # Restrict .env file access
   sudo chmod 600 /opt/xrate/.env
   sudo chown xrate:xrate /opt/xrate/.env
   ```

2. **Firewall:**
   - Bot only needs outbound HTTPS access (no inbound ports)
   - Allow outbound connections to `api.telegram.org` and API providers

3. **Service User:**
   - Bot runs as dedicated `xrate` user (not root)
   - Service user has limited permissions

4. **Systemd Security:**
   - Service uses `PrivateTmp`, `ProtectSystem=strict`
   - Only `/opt/xrate/data` is writable

## 📊 Monitoring

### Health Checks

The bot provides a `/health` command that you can use to monitor status.

### Log Monitoring

Set up log rotation and monitoring:

```bash
# For systemd, logs are automatically managed
# For supervisor, configure logrotate for /opt/xrate/logs/
```

### Resource Usage

Monitor bot resource usage:

```bash
# CPU and memory
ps aux | grep xrate

# Or with systemd
systemctl status xrate
```

## 🔗 Additional Resources

- Project README: `/opt/xrate/README.md`
- Service files: `/opt/xrate/deploy/`
- Logs: `/opt/xrate/logs/` or `journalctl -u xrate`

## 📞 Support

For issues or questions:
1. Check logs first
2. Review this deployment guide
3. Check the main README.md
4. Review service configuration files

