# Deakyne.me Service Setup

This directory contains configuration files and scripts to run deakyne.me as system services on macOS using launchd.

## Architecture

```
┌─────────────────┐
│  Cloudflare     │
│  Tunnel         │  (system service)
│  Port: public   │
└────────┬────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
         ▼                                 ▼
┌─────────────────┐              ┌─────────────────┐
│  Next.js        │              │  FastAPI        │
│  Frontend       │◄─────────────│  Backend        │
│  Port: 3000     │  (proxied)   │  Port: 8000     │
└─────────────────┘              └─────────────────┘
  (user service)                   (user service)
```

## Services

### 1. Cloudflare Tunnel (`com.cloudflare.cloudflared`)
- **Type**: System daemon (runs as root)
- **Purpose**: Exposes deakyne.me to the internet via Cloudflare
- **Config**: `~/.cloudflared/config.yml`
- **Logs**: `logs/cloudflared.log`

### 2. FastAPI Backend (`com.deakyne.backend`)
- **Type**: User agent
- **Purpose**: API backend with JWT authentication
- **Port**: 8000 (localhost only)
- **Logs**: `logs/backend.log`

### 3. Next.js Frontend (`com.deakyne.frontend`)
- **Type**: User agent
- **Purpose**: Web interface with terminal emulator
- **Port**: 3000 (localhost only)
- **Logs**: `logs/frontend.log`

## Installation

### Prerequisites
1. Built Next.js application: `npm run build`
2. Python virtual environment with dependencies installed in `backend/.venv`
3. Cloudflare tunnel configured at `~/.cloudflared/config.yml`

### Install All Services

Run the setup script with sudo:

```bash
cd /Users/matt/Development/deakyne.me/services
sudo bash setup-services.sh
```

This will:
1. Build the Next.js frontend
2. Install all three services
3. Start them automatically
4. Configure them to start on boot

## Management Commands

### Check Status
```bash
bash status.sh
```

Shows running status, PIDs, ports, and recent log entries.

### Restart Services
```bash
sudo bash restart-services.sh
```

Restarts all three services.

### Stop Services
```bash
sudo bash stop-services.sh
```

Stops all services (they won't restart on boot).

### View Logs
```bash
# All logs
tail -f ../logs/*.log

# Specific service
tail -f ../logs/cloudflared.log
tail -f ../logs/backend.log
tail -f ../logs/frontend.log
```

## Manual Service Management

### Cloudflare Tunnel (System Service)
```bash
# Start
sudo launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared.plist

# Stop
sudo launchctl bootout system/com.cloudflare.cloudflared

# Restart
sudo launchctl kickstart -k system/com.cloudflare.cloudflared

# Status
sudo launchctl print system/com.cloudflare.cloudflared

# View logs
tail -f ../logs/cloudflared.log
```

### Backend API (User Service)
```bash
# Start
launchctl bootstrap gui/$(id -u) /Library/LaunchAgents/com.deakyne.backend.plist

# Stop
launchctl bootout gui/$(id -u)/com.deakyne.backend

# Restart
launchctl kickstart -k gui/$(id -u)/com.deakyne.backend

# Status
launchctl print gui/$(id -u)/com.deakyne.backend

# View logs
tail -f ../logs/backend.log
```

### Frontend (User Service)
```bash
# Start
launchctl bootstrap gui/$(id -u) /Library/LaunchAgents/com.deakyne.frontend.plist

# Stop
launchctl bootout gui/$(id -u)/com.deakyne.frontend

# Restart
launchctl kickstart -k gui/$(id -u)/com.deakyne.frontend

# Status
launchctl print gui/$(id -u)/com.deakyne.frontend

# View logs
tail -f ../logs/frontend.log
```

## Updating Code

When you update the code:

### Backend Changes
```bash
cd backend
# Update code...
launchctl kickstart -k gui/$(id -u)/com.deakyne.backend
```

### Frontend Changes
```bash
npm run build
launchctl kickstart -k gui/$(id -u)/com.deakyne.frontend
```

### Cloudflare Config Changes
```bash
# Edit ~/.cloudflared/config.yml
cloudflared tunnel ingress validate
sudo launchctl kickstart -k system/com.cloudflare.cloudflared
```

## Troubleshooting

### Service Won't Start

Check the error logs:
```bash
cat logs/backend-error.log
cat logs/frontend-error.log
cat logs/cloudflared-error.log
```

### Port Already in Use

Kill any manual processes:
```bash
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### Frontend Build Issues

Make sure Next.js is built:
```bash
npm run build
```

### Backend Environment Issues

Verify `.env` file exists in `backend/`:
```bash
cat backend/.env
```

### Cloudflare Tunnel Not Connecting

Test the tunnel manually:
```bash
cloudflared tunnel --config ~/.cloudflared/config.yml run
```

Check DNS records are pointing to the tunnel:
```bash
cloudflared tunnel route dns list
```

## DNS Setup

If DNS isn't configured yet, set up the tunnel route:

```bash
cloudflared tunnel route dns matt-fastapi deakyne.me
cloudflared tunnel route dns matt-fastapi www.deakyne.me
```

## Uninstalling Services

To completely remove the services:

```bash
# Stop services
sudo bash stop-services.sh

# Remove plist files
sudo rm /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo rm /Library/LaunchAgents/com.deakyne.backend.plist
sudo rm /Library/LaunchAgents/com.deakyne.frontend.plist
```

## Security Notes

- Backend API only listens on localhost (127.0.0.1)
- All external traffic goes through Cloudflare Tunnel
- JWT tokens are stored in SQLite database (`backend/api_keys.db`)
- SMTP credentials are in `backend/.env` (never commit this!)
