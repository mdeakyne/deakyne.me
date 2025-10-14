# Cloudflare Tunnel Setup Checklist for deakyne.me

## Quick Start

Run these commands to set everything up:

```bash
cd /Users/matt/Development/deakyne.me/services
sudo bash setup-services.sh
```

Then check status:
```bash
bash status.sh
```

## Manual Step-by-Step Setup

If you prefer to do it manually or the script fails:

### 1. Prepare the Application

```bash
cd /Users/matt/Development/deakyne.me

# Build Next.js for production
npm run build

# Verify backend virtual environment exists
ls backend/.venv/bin/uvicorn

# Create logs directory
mkdir -p logs
```

### 2. Verify Cloudflare Config

```bash
# Check config is valid
cloudflared tunnel ingress validate

# View current config
cat ~/.cloudflared/config.yml
```

### 3. Set up DNS (if not already done)

```bash
# Route deakyne.me to your tunnel
cloudflared tunnel route dns matt-fastapi deakyne.me

# Route www.deakyne.me to your tunnel
cloudflared tunnel route dns matt-fastapi www.deakyne.me

# Verify routes
cloudflared tunnel info matt-fastapi
```

### 4. Install Services

```bash
cd /Users/matt/Development/deakyne.me/services

# Install Cloudflare Tunnel (system service)
sudo cp com.cloudflare.cloudflared.plist /Library/LaunchDaemons/
sudo chown root:wheel /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo chmod 644 /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl enable system/com.cloudflare.cloudflared

# Install Backend service (user service)
sudo cp com.deakyne.backend.plist /Library/LaunchAgents/
sudo chown root:wheel /Library/LaunchAgents/com.deakyne.backend.plist
sudo chmod 644 /Library/LaunchAgents/com.deakyne.backend.plist
launchctl bootstrap gui/$(id -u) /Library/LaunchAgents/com.deakyne.backend.plist
launchctl enable gui/$(id -u)/com.deakyne.backend

# Install Frontend service (user service)
sudo cp com.deakyne.frontend.plist /Library/LaunchAgents/
sudo chown root:wheel /Library/LaunchAgents/com.deakyne.frontend.plist
sudo chmod 644 /Library/LaunchAgents/com.deakyne.frontend.plist
launchctl bootstrap gui/$(id -u) /Library/LaunchAgents/com.deakyne.frontend.plist
launchctl enable gui/$(id -u)/com.deakyne.frontend
```

### 5. Start Services

```bash
# Start Cloudflare Tunnel
sudo launchctl kickstart system/com.cloudflare.cloudflared

# Start Backend
launchctl kickstart gui/$(id -u)/com.deakyne.backend

# Start Frontend
launchctl kickstart gui/$(id -u)/com.deakyne.frontend
```

### 6. Verify Services are Running

```bash
# Check all services
bash status.sh

# Or check individually
sudo launchctl print system/com.cloudflare.cloudflared | grep "state ="
launchctl print gui/$(id -u)/com.deakyne.backend | grep "state ="
launchctl print gui/$(id -u)/com.deakyne.frontend | grep "state ="
```

### 7. Check Logs

```bash
cd /Users/matt/Development/deakyne.me

# View all logs in real-time
tail -f logs/*.log

# Or check individual logs
tail -f logs/cloudflared.log
tail -f logs/backend.log
tail -f logs/frontend.log

# Check error logs if something fails
cat logs/cloudflared-error.log
cat logs/backend-error.log
cat logs/frontend-error.log
```

### 8. Test the Setup

```bash
# Test local backend
curl http://localhost:8000/api/profile

# Test local frontend
curl http://localhost:3000

# Test public domain (after DNS propagates)
curl https://deakyne.me
```

## Verification Checklist

- [ ] Next.js built successfully (`npm run build`)
- [ ] Backend .env file exists with SMTP credentials
- [ ] Cloudflare config validates (`cloudflared tunnel ingress validate`)
- [ ] DNS routes configured for deakyne.me and www.deakyne.me
- [ ] All three services installed and enabled
- [ ] Backend responding on http://localhost:8000
- [ ] Frontend responding on http://localhost:3000
- [ ] Cloudflare tunnel shows "state = running"
- [ ] Site accessible at https://deakyne.me
- [ ] Can request API key via terminal
- [ ] Can authenticate and call API endpoints
- [ ] Mail command works and sends emails

## Common Issues

### "Address already in use"
```bash
# Kill any manual processes
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### "No such file or directory" for uvicorn
```bash
# Reinstall backend dependencies
cd backend
uv pip install -r requirements.txt
```

### Frontend won't start
```bash
# Rebuild Next.js
npm run build

# Check for port conflicts
lsof -ti:3000
```

### Cloudflare tunnel not connecting
```bash
# Test tunnel manually
cloudflared tunnel --config ~/.cloudflared/config.yml run

# Check credentials
ls -la ~/.cloudflared/502cd188-df5e-43d9-a57f-a43658932984.json
```

### Services not starting on boot
```bash
# Re-enable services
sudo launchctl enable system/com.cloudflare.cloudflared
launchctl enable gui/$(id -u)/com.deakyne.backend
launchctl enable gui/$(id -u)/com.deakyne.frontend
```

## Directory Structure

```
/Users/matt/Development/deakyne.me/
├── app/                          # Next.js pages
├── backend/                      # FastAPI backend
│   ├── .venv/                   # Python virtual environment
│   ├── .env                     # Environment variables
│   ├── main.py                  # FastAPI app
│   └── api_keys.db             # SQLite database
├── components/                   # React components
├── lib/                         # Frontend utilities
├── logs/                        # Service logs
│   ├── cloudflared.log
│   ├── cloudflared-error.log
│   ├── backend.log
│   ├── backend-error.log
│   ├── frontend.log
│   └── frontend-error.log
└── services/                    # This directory
    ├── com.cloudflare.cloudflared.plist
    ├── com.deakyne.backend.plist
    ├── com.deakyne.frontend.plist
    ├── setup-services.sh
    ├── restart-services.sh
    ├── stop-services.sh
    ├── status.sh
    ├── README.md
    └── SETUP-CHECKLIST.md (this file)

/Library/LaunchDaemons/
└── com.cloudflare.cloudflared.plist (installed copy)

/Library/LaunchAgents/
├── com.deakyne.backend.plist (installed copy)
└── com.deakyne.frontend.plist (installed copy)

~/.cloudflared/
├── config.yml                   # Tunnel configuration
├── cert.pem                     # Cloudflare certificate
└── 502cd188-df5e-43d9-a57f-a43658932984.json  # Tunnel credentials
```
