# Deakyne.me - Developer Portal

Interactive terminal-based developer portal for the Deakyne.me API. Features real terminal emulation, JWT authentication via email, and interactive API exploration.

## Features

- **Real Terminal Emulator** - Powered by xterm.js
- **JWT Authentication** - Request API keys via email
- **Interactive API Documentation** - Test endpoints directly from the terminal
- **Terminal Theme** - Retro green-on-black aesthetic
- **Command System** - Intuitive CLI-style interface

## Tech Stack

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **xterm.js** - Terminal emulator

### Backend
- **FastAPI** - Python API framework
- **JWT** - Authentication tokens
- **SMTP** - Email delivery

## Quick Start

### Prerequisites
- Node.js 22 (managed with [`nvm`](https://github.com/nvm-sh/nvm))
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (Python package manager)

### Frontend Setup

```bash
# Ensure the correct Node.js version
source ~/.nvm/nvm.sh
nvm use 22

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit http://localhost:3000

### Backend Setup

```bash
cd backend

# Create or reuse a virtualenv managed by uv
uv venv .venv

# Install dependencies (including PostHog SDK)
uv pip install --python .venv/bin/python fastapi>=0.115.0 uvicorn[standard]>=0.32.0 \
  python-jose[cryptography]>=3.3.0 passlib[bcrypt]>=1.7.4 python-multipart>=0.0.12 \
  pydantic>=2.10.0 pydantic-settings>=2.6.0 python-dotenv>=1.0.0 httpx>=0.27.0 \
  posthog>=3.5.0

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# For development, you can leave SMTP settings empty - tokens will print to console

# Run backend
uv run python main.py
```

Backend runs on http://localhost:8000

### Metrics Dashboard

Once both services are running, authenticate in the terminal and run:

```bash
metrics
```

The dashboard combines local SQLite aggregations with PostHog analytics. The backend proxies PostHog via `/api/metrics/*`, and the frontend mirrors those metrics in the ASCII view. For deeper visualizations, use the PostHog dashboard referenced in the environment variables.

## Available Terminal Commands

```bash
help                    # Show available commands
docs                    # Browse API documentation
request-key <email>     # Request JWT via email
auth <token>           # Authenticate with JWT
api list               # List available API endpoints
api call <endpoint>    # Make API call
api docs <endpoint>    # Show endpoint documentation
metrics                # View API metrics dashboard
logout                 # Clear authentication
clear                  # Clear terminal screen
```

## Usage Flow

1. Open terminal at https://deakyne.me
2. Type `request-key your@email.com`
3. Check your email for the JWT token
4. Type `auth <your-token>` to authenticate
5. Use `api list` to see available endpoints
6. Test APIs with `api call <endpoint>`

## Development

### Frontend
```bash
npm run dev      # Start dev server
npm run build    # Build for production
npm run start    # Start production server
```

### Backend
```bash
cd backend
uv run python main.py        # Start dev server
uv run uvicorn main:app      # Alternative start
```

## Configuration

### Backend Environment Variables

```env
# JWT Settings
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=168

# Email Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@deakyne.me

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# PostHog (server-side)
POSTHOG_PROJECT_API_KEY=phc_server_key
POSTHOG_HOST=https://us.i.posthog.com
POSTHOG_PROJECT_ID=123
POSTHOG_API_KEY=phx_personal_api_key

# Database
DB_PATH=backend/api_keys.db
```

### Frontend Environment Variables

Create `.env.local`:
```env
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_POSTHOG_KEY=phc_public_key
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
NEXT_PUBLIC_POSTHOG_DASHBOARD_URL=https://app.posthog.com/project/123/dashboard
```

> **Note:** If you want to avoid generating PostHog person profiles for public traffic, set the `$process_person_profile` property to `false` when capturing events (the integration in this repo does this by default).

## Deployment

### Frontend (Cloudflare Tunnel)
The frontend is deployed via Cloudflare Tunnel with a launchd service on macOS:

```bash
# Tunnel configuration
~/.cloudflared/config.yml

# Service management
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl start com.cloudflare.cloudflared
```

The tunnel points to `localhost:3000` where the Next.js dev server runs.

### Backend (Local Service)
The FastAPI backend runs as a local service via launchd:

```bash
# Service file location
~/Library/LaunchAgents/com.deakyne.backend.plist

# Service management
launchctl load ~/Library/LaunchAgents/com.deakyne.backend.plist
launchctl start com.deakyne.backend
```

### Production Build
For production deployment:

```bash
# Frontend
npm run build
npm run start

# Backend
cd backend
uv run python main.py
```

## Email Setup (Gmail)

1. Enable 2FA on your Google account
2. Generate an app password: https://myaccount.google.com/apppasswords
3. Use the app password in `SMTP_PASSWORD`

## Project Structure

```
deakyne.me/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # React components
│   └── Terminal.tsx       # Terminal emulator
├── lib/                   # Utilities
│   └── commands.ts        # Terminal command system
├── backend/              # FastAPI backend
│   ├── main.py           # API server
│   ├── pyproject.toml    # Python dependencies
│   └── .env.example      # Environment template
└── README.md
```

## License

Copyright © 2025 Matt Deakyne. All rights reserved.
