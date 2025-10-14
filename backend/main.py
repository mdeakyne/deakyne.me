"""
FastAPI backend for Deakyne.me developer portal
Handles JWT generation and email distribution
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Deakyne.me API",
    description="Developer portal backend for API key management",
    version="1.0.0"
)

# CORS configuration
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "168"))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@deakyne.me")


class KeyRequest(BaseModel):
    email: EmailStr


class KeyResponse(BaseModel):
    message: str
    status: str


def create_jwt_token(email: str) -> str:
    """Generate a JWT token for the given email"""
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "sub": email,
        "exp": expiration,
        "iat": datetime.utcnow(),
        "type": "api_key"
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def send_email(to_email: str, token: str):
    """Send JWT token via email"""
    subject = "Your Deakyne.me API Key"

    # Create HTML email body
    html_body = f"""
    <html>
        <body style="font-family: 'Courier New', monospace; background-color: #0a0e14; color: #00ff00; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #1a1e24; padding: 30px; border: 2px solid #00ff00; border-radius: 8px;">
                <h1 style="color: #00ff00; margin-bottom: 20px;">Welcome to Deakyne.me Developer Portal</h1>

                <p style="line-height: 1.6;">Your API authentication key has been generated.</p>

                <div style="background-color: #0a0e14; padding: 15px; margin: 20px 0; border-left: 4px solid #00ff00; font-family: monospace; word-break: break-all;">
                    {token}
                </div>

                <h3 style="color: #00ffff; margin-top: 30px;">How to use:</h3>
                <ol style="line-height: 1.8;">
                    <li>Copy the token above</li>
                    <li>Return to the terminal at <a href="https://deakyne.me" style="color: #00ffff;">deakyne.me</a></li>
                    <li>Type: <code style="background-color: #0a0e14; padding: 2px 6px; color: #ffff00;">auth &lt;your-token&gt;</code></li>
                    <li>Press Enter to authenticate</li>
                </ol>

                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #00ff00; color: #888; font-size: 12px;">
                    This token expires in {JWT_EXPIRATION_HOURS} hours.<br>
                    If you didn't request this token, you can safely ignore this email.
                </p>
            </div>
        </body>
    </html>
    """

    # Create plain text version
    text_body = f"""
Your Deakyne.me API Key

Your authentication token:
{token}

How to use:
1. Copy the token above
2. Return to the terminal at deakyne.me
3. Type: auth <your-token>
4. Press Enter to authenticate

This token expires in {JWT_EXPIRATION_HOURS} hours.
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email

    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')

    msg.attach(part1)
    msg.attach(part2)

    # Send email
    if not SMTP_USER or not SMTP_PASSWORD:
        # Development mode - just print token
        print(f"\n{'='*60}")
        print("DEVELOPMENT MODE - Email not configured")
        print(f"{'='*60}")
        print(f"To: {to_email}")
        print(f"Token: {token}")
        print(f"{'='*60}\n")
        return

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "operational",
        "service": "Deakyne.me API",
        "version": "1.0.0"
    }


@app.post("/api/request-key", response_model=KeyResponse)
async def request_key(request: KeyRequest):
    """Generate and email a JWT token"""
    try:
        # Generate JWT token
        token = create_jwt_token(request.email)

        # Send email with token
        send_email(request.email, token)

        return KeyResponse(
            message=f"API key sent to {request.email}",
            status="success"
        )

    except Exception as e:
        print(f"Error in request_key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process request. Please try again later."
        )


@app.post("/api/validate-token")
async def validate_token(token: str):
    """Validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {
            "valid": True,
            "email": payload.get("sub"),
            "expires": payload.get("exp")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
