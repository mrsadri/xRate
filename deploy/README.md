# Deployment Files

This directory contains files and scripts for deploying the XRate bot to a production server.

## Files

- **`xrate.service`** - systemd service file
- **`supervisor-xrate.conf`** - Supervisor configuration file
- **`deploy.sh`** - Automated deployment script
- **`SERVER_DEPLOYMENT.md`** - Complete deployment guide

## Quick Start

1. Copy the deployment script to your server
2. Run: `sudo ./deploy/deploy.sh systemd`
3. Configure `.env` file
4. Start service: `sudo systemctl start xrate`

See `SERVER_DEPLOYMENT.md` for detailed instructions.

