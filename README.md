# Deakyne.me - Developer Portal

Interactive terminal-based developer portal for the Deakyne.Dev API. Features real terminal emulation, JWT authentication via email, and interactive API exploration.

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
- Node.js 20+
- Python 3.11+
- uv (Python package manager)

### Frontend Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Visit http://localhost:3000

### Backend Setup

```bash
cd backend

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# For development, you can leave SMTP settings empty - tokens will print to console

# Run backend
uv run python main.py
```

Backend runs on http://localhost:8000

## Available Terminal Commands

```bash
help                    # Show available commands
docs                    # Browse API documentation
request-key <email>     # Request JWT via email
auth <token>           # Authenticate with JWT
api list               # List available API endpoints
api call <endpoint>    # Make API call
api docs <endpoint>    # Show endpoint documentation
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

# Deakyne.Dev API
DEAKYNE_DEV_API_URL=https://deakyne.dev/api
```

### Frontend Environment Variables

Create `.env.local`:
```env
BACKEND_URL=http://localhost:8000
```

## Deployment

### Frontend (Vercel)
```bash
vercel deploy
```

### Backend (Railway/Fly.io)
Configure environment variables and deploy:
```bash
# Railway
railway up

# Fly.io
fly deploy
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
