# 🚀 Quick Start - Deakyne.me Cloudflare Tunnel

## TL;DR - Run This

```bash
cd /Users/matt/Development/deakyne.me/services
sudo bash setup-services.sh
bash status.sh
```

## What Was Set Up

### Files Created

**Service Definitions** (in `/Users/matt/Development/deakyne.me/services/`):
- `com.cloudflare.cloudflared.plist` - Cloudflare tunnel service config
- `com.deakyne.backend.plist` - FastAPI backend service config
- `com.deakyne.frontend.plist` - Next.js frontend service config

**Management Scripts**:
- `setup-services.sh` - One-command setup (run with sudo)
- `status.sh` - Check service status
- `restart-services.sh` - Restart all services (run with sudo)
- `stop-services.sh` - Stop all services (run with sudo)

**Documentation**:
- `README.md` - Comprehensive documentation
- `SETUP-CHECKLIST.md` - Step-by-step manual setup
- `QUICK-START.md` - This file

### Cloudflare Config Updated

Updated `~/.cloudflared/config.yml` to route:
- `deakyne.me` → `http://localhost:3000`
- `www.deakyne.me` → `http://localhost:3000`

The Next.js app on port 3000 proxies API requests to the backend on port 8000.

## Service Architecture

```
                    Internet
                       ↓
              ┌────────────────┐
              │   Cloudflare   │
              │     Tunnel     │
              │ (port: public) │
              └────────┬───────┘
                       ↓
              https://deakyne.me
                       ↓
              ┌────────────────┐      ┌────────────────┐
              │    Next.js     │─────→│    FastAPI     │
              │   Frontend     │      │    Backend     │
              │  localhost:3000│      │ localhost:8000 │
              └────────────────┘      └────────────────┘
```

## Installation

### Step 1: Run Setup Script

```bash
cd /Users/matt/Development/deakyne.me/services
sudo bash setup-services.sh
```

This will:
- Build Next.js for production
- Install all three services
- Start them immediately
- Configure them to auto-start on boot

### Step 2: Verify Everything Works

```bash
bash status.sh
```

You should see all three services showing "✅ Running".

### Step 3: Test Locally

```bash
# Test backend API
curl http://localhost:8000/api/profile

# Test frontend
curl http://localhost:3000

# View logs
tail -f ../logs/*.log
```

### Step 4: Configure DNS (if needed)

If DNS isn't configured yet:

```bash
cloudflared tunnel route dns matt-fastapi deakyne.me
cloudflared tunnel route dns matt-fastapi www.deakyne.me
```

### Step 5: Test Public Access

Wait a few minutes for DNS to propagate, then:

```bash
curl https://deakyne.me
```

Or visit https://deakyne.me in your browser!

## Daily Commands

### Check Status
```bash
cd /Users/matt/Development/deakyne.me/services
bash status.sh
```

### View Logs
```bash
cd /Users/matt/Development/deakyne.me
tail -f logs/*.log
```

### Restart After Code Changes

**Backend only:**
```bash
launchctl kickstart -k gui/$(id -u)/com.deakyne.backend
```

**Frontend only:**
```bash
cd /Users/matt/Development/deakyne.me
npm run build
launchctl kickstart -k gui/$(id -u)/com.deakyne.frontend
```

**Everything:**
```bash
cd /Users/matt/Development/deakyne.me/services
sudo bash restart-services.sh
```

## Troubleshooting

### Services won't start?
```bash
# Check error logs
cat /Users/matt/Development/deakyne.me/logs/*-error.log

# Try manual restart
cd /Users/matt/Development/deakyne.me/services
sudo bash restart-services.sh
```

### Port conflicts?
```bash
# Kill manual processes
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Restart services
cd /Users/matt/Development/deakyne.me/services
sudo bash restart-services.sh
```

### Need to stop everything?
```bash
cd /Users/matt/Development/deakyne.me/services
sudo bash stop-services.sh
```

## What Happens on Reboot?

All three services are configured to start automatically:
1. **Cloudflare Tunnel** starts as a system daemon (runs as root)
2. **Backend API** starts as a user service when you log in
3. **Frontend** starts as a user service when you log in

Your site will be live immediately after boot!

## Next Steps

1. Test the terminal interface at https://deakyne.me
2. Request an API key with `request-key your@email.com`
3. Authenticate with the token from your email
4. Try the `mail` command to send yourself a message
5. Monitor logs to see API calls: `tail -f logs/backend.log`

## Help

- Full documentation: `services/README.md`
- Manual setup guide: `services/SETUP-CHECKLIST.md`
- Check service status: `bash services/status.sh`
