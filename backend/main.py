"""
FastAPI backend for Deakyne.me developer portal
Handles JWT generation, email distribution, and metrics logging
"""
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from typing import Optional
import sqlite3
from contextlib import contextmanager
try:
    from backend.logging_middleware import LoggingMiddleware  # type: ignore
except ImportError:
    from logging_middleware import LoggingMiddleware  # type: ignore

load_dotenv()

# Database setup
DB_PATH = os.getenv("DB_PATH", "api_keys.db")

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table for storing email-token pairs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        )
    """)

    # Table for logging API calls
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            response_time_ms INTEGER,
            status_code INTEGER,
            user_agent TEXT,
            request_id TEXT
        )
    """)

    # Backfill missing columns for existing installations
    cursor.execute("PRAGMA table_info(api_logs)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    column_defs = {
        "response_time_ms": "INTEGER",
        "status_code": "INTEGER",
        "user_agent": "TEXT",
        "request_id": "TEXT"
    }
    for column_name, column_type in column_defs.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE api_logs ADD COLUMN {column_name} {column_type}")

    # Aggregated metrics tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_metrics (
            date DATE PRIMARY KEY,
            total_calls INTEGER,
            unique_users INTEGER,
            avg_response_time_ms REAL,
            error_rate REAL,
            refreshed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS endpoint_metrics (
            date DATE,
            endpoint TEXT,
            total_calls INTEGER,
            avg_response_time_ms REAL,
            error_rate REAL,
            error_count INTEGER,
            PRIMARY KEY (date, endpoint)
        )
    """)
    cursor.execute("PRAGMA table_info(endpoint_metrics)")
    endpoint_columns = {row[1] for row in cursor.fetchall()}
    if "error_count" not in endpoint_columns:
        cursor.execute("ALTER TABLE endpoint_metrics ADD COLUMN error_count INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

app = FastAPI(
    title="Deakyne.me API",
    description="Developer portal backend for API key management",
    version="1.0.0"
)

# Initialize database on startup
init_db()
app.add_middleware(LoggingMiddleware, db_factory=get_db)

try:
    from backend.routes import metrics as metrics_routes
except ImportError:
    from routes import metrics as metrics_routes

metrics_routes.configure(get_db)
app.include_router(metrics_routes.router)

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
    """Generate and email a JWT token, or resend existing one"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check if email already has a token
            cursor.execute("SELECT token FROM api_keys WHERE email = ?", (request.email,))
            result = cursor.fetchone()

            if result:
                # Reuse existing token
                token = result['token']
                print(f"Reusing existing token for {request.email}")
            else:
                # Generate new JWT token
                token = create_jwt_token(request.email)

                # Store in database
                cursor.execute(
                    "INSERT INTO api_keys (email, token) VALUES (?, ?)",
                    (request.email, token)
                )
                conn.commit()
                print(f"Generated new token for {request.email}")

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


class TokenValidation(BaseModel):
    token: str


class MailMessage(BaseModel):
    message: str


@app.post("/api/validate-token")
async def validate_token(data: TokenValidation):
    """Validate a JWT token"""
    try:
        payload = jwt.decode(data.token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {
            "valid": True,
            "email": payload.get("sub"),
            "expires": payload.get("exp")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_token(token: str) -> dict:
    """Helper function to verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Update last_used timestamp for this token
        email = payload.get("sub")
        if email:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE email = ?",
                    (email,)
                )
                conn.commit()

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_auth(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> str:
    """Dependency to verify JWT tokens and attach context to the request."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    payload = verify_token(token)
    email = payload.get("sub")

    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    request.state.auth_email = email
    request.state.bearer_token = token

    return email


@app.get("/api/profile")
async def get_profile(email: str = Depends(require_auth)):
    """Get basic profile information"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "profile": {
                "name": "Matthew Deakyne",
                "location": "Lawrence, Kansas",
                "email": "mdeakyne@gmail.com",
                "phone": "408-372-6366",
                "personal_brand": "People. Data. Story.",
                "headline": "Technical Educator | Data Evangelist | Automation Strategist",
                "summary": "Technologist and educator with over a decade of experience designing scalable data systems, automation frameworks, and learning programs that make complex technology approachable and impactful."
            }
        }
    }


@app.get("/api/summary")
async def get_professional_summary(email: str = Depends(require_auth)):
    """Get professional summary and core strengths"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "professional_summary": {
                "overview": "Senior leader at the intersection of education, data, and automation. Experienced in evangelism, managed services, and technical consulting across SaaS and higher education sectors.",
                "mission": "To connect people, data, and systems in ways that accelerate learning, simplify complexity, and scale understanding.",
                "core_strengths": [
                    "Building scalable education frameworks and managed services programs",
                    "Evangelizing complex technologies through storytelling and data visualization",
                    "Designing modern analytics pipelines using Python, SQL, and automation platforms",
                    "Translating customer needs into actionable product and data strategies"
                ]
            }
        }
    }


@app.get("/api/experience")
async def get_experience(email: str = Depends(require_auth)):
    """Get work experience and positions"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "experience": {
                "positions": [
                    {
                        "title": "Manager, Customer Enablement (Evangelism + Managed Services)",
                        "company": "TeamDynamix",
                        "start_date": "2022-05",
                        "end_date": "Present",
                        "location": "Remote / Columbus, OH",
                        "summary": "Lead evangelism and managed services teams, driving customer adoption of iPaaS and CAI automation platforms.",
                        "achievements": [
                            "Developed and scaled the Managed Services model, embedding technical consultants with clients.",
                            "Built evangelism programs and workshops driving engagement across customer communities.",
                            "Created data pipelines and dashboards for executive reporting on adoption, engagement, and renewal metrics.",
                            "Collaborated with Product and Engineering to translate customer feedback into roadmap priorities."
                        ]
                    },
                    {
                        "title": "Principal Analyst",
                        "company": "University of Kansas",
                        "start_date": "2021-10",
                        "end_date": "2022-04",
                        "summary": "Modernized the university's analytics ecosystem through migration of SAS to Python-based reporting.",
                        "achievements": [
                            "Maintained enterprise dashboards in Tableau and Oracle Analytics Cloud.",
                            "Built predictive models and self-service analytics training materials for research teams.",
                            "Introduced modern code-sharing practices through Jupyter and GitLab CI/CD."
                        ]
                    },
                    {
                        "title": "Academic and Service Systems Manager",
                        "company": "University of Kansas",
                        "start_date": "2018-07",
                        "end_date": "2021-10",
                        "summary": "Managed integrations, education programs, and agile development processes for enterprise systems.",
                        "achievements": [
                            "Developed data pipelines and automation integrations across university systems.",
                            "Implemented agile workflows for distributed technical teams.",
                            "Mentored staff in analytics and API-driven design thinking."
                        ]
                    },
                    {
                        "title": "Lead Educational Technologist",
                        "company": "University of Kansas",
                        "start_date": "2016-03",
                        "end_date": "2018-07",
                        "summary": "Architected educational technology integrations and published open-source developer tools.",
                        "achievements": [
                            "Created and published an SDK for Blackboard REST APIs, expanding global developer adoption.",
                            "Delivered workshops and training sessions for educational technology staff.",
                            "Developed analytics reporting via REST APIs and SQL."
                        ]
                    },
                    {
                        "title": "Program Director, Computer Information Systems",
                        "company": "University of Saint Mary",
                        "start_date": "2012-08",
                        "end_date": "2016-05",
                        "summary": "Redesigned the CIS curriculum to align with industry standards and scalable pedagogy.",
                        "achievements": [
                            "Taught and developed computer science and education courses.",
                            "Integrated modern tools, languages, and professional practices into coursework.",
                            "Established program metrics for student success and engagement."
                        ]
                    }
                ]
            }
        }
    }


@app.get("/api/education")
async def get_education(email: str = Depends(require_auth)):
    """Get education and degrees"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "education": {
                "degrees": [
                    {
                        "degree": "Master of Science in Applied Statistics & Data Science",
                        "institution": "University of Kansas Medical Center",
                        "year": 2021,
                        "gpa": 4.0
                    },
                    {
                        "degree": "Master of Arts in Education (Adult Education)",
                        "institution": "University of Saint Mary",
                        "year": 2014,
                        "gpa": 4.0
                    },
                    {
                        "degree": "Bachelor of Science in Computer Science (Minor in English)",
                        "institution": "Iowa State University",
                        "year": 2008,
                        "gpa": 3.5
                    }
                ]
            }
        }
    }


@app.get("/api/skills")
async def get_skills(email: str = Depends(require_auth)):
    """Get technical skills and tools"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "skills": {
                "languages": ["Python", "SQL", "R", "Java"],
                "frameworks": ["FastAPI", "SQLAlchemy", "Pandas", "Streamlit", "Jupyter", "HvPlot"],
                "data_platforms": ["Snowflake", "Tableau", "Power BI", "Oracle Analytics Cloud", "Canvas Data"],
                "automation_platforms": ["TeamDynamix iPaaS", "Zapier", "n8n", "Microsoft Power Automate"],
                "tools": ["GitLab CI/CD", "Docker", "REST APIs", "Datadog", "Asana", "Salesforce"],
                "specializations": [
                    "Data pipeline design and orchestration",
                    "No-code / low-code automation",
                    "Technical education program design",
                    "Data visualization and storytelling",
                    "Community and developer evangelism"
                ]
            }
        }
    }


@app.get("/api/competencies")
async def get_competencies(email: str = Depends(require_auth)):
    """Get core competencies and leadership areas"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "competencies": {
                "education_leadership": [
                    "Scalable enablement and learning program design",
                    "Train-the-trainer frameworks and certifications",
                    "Hybrid learning model integration (asynchronous + live)"
                ],
                "data_and_automation": [
                    "End-to-end pipeline architecture",
                    "API integrations and orchestration",
                    "Data-driven reporting and metrics frameworks"
                ],
                "evangelism_and_community": [
                    "Developer engagement and education",
                    "Public speaking, demos, and conference content",
                    "Product feedback and feature advocacy"
                ],
                "collaboration": [
                    "Cross-functional leadership across Product, Sales, and Customer Success",
                    "Executive communication and data storytelling",
                    "Strategic planning and operational execution"
                ]
            }
        }
    }


@app.get("/api/projects")
async def get_projects(email: str = Depends(require_auth)):
    """Get portfolio projects"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "projects": [
                {
                    "name": "FlowMart Data Dashboard",
                    "description": "A suite of analytics dashboards visualizing flow and automation adoption across enterprise customers using Polars and hvPlot.",
                    "tech": ["Python", "SQL", "DuckDB", "hvPlot", "Kendo UI"]
                },
                {
                    "name": "Matt API",
                    "description": "Personal API and FastAPI backend powering deakyne.dev and deakyne.me, with endpoints for resume, reading lists, and automation demos.",
                    "tech": ["FastAPI", "Polars", "SQLite", "Cloudflare Pages", "Tailscale"]
                },
                {
                    "name": "Managed Services Portal",
                    "description": "Internal Kendo UI portal for tracking Managed Services engagements, time tracking, and customer performance metrics.",
                    "tech": ["Kendo UI", "iPaaS", "SQL Server", "Azure"]
                },
                {
                    "name": "F3 Fitness Deck",
                    "description": "A custom-designed card workout generator mapping 52 exercises to a deck of cards, blending fitness gamification and data tracking.",
                    "tech": ["Python", "Notion API", "HTML Canvas"]
                }
            ]
        }
    }


@app.get("/api/hobbies")
async def get_hobbies(email: str = Depends(require_auth)):
    """Get hobbies and interests"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "hobbies": {
                "creative_projects": [
                    "Building custom APIs and automation agents",
                    "Designing card-based games and D&D story arcs",
                    "Creating personal analytics dashboards and tools"
                ],
                "physical_activities": [
                    "F3 workouts (bodyweight fitness, rucking, Tabata)",
                    "Cycling and swimming",
                    "DIY home projects and woodworking"
                ],
                "family_and_community": [
                    "Raising chickens and gardening with my family",
                    "Church involvement and small group leadership",
                    "Mentoring in tech education and community learning"
                ]
            }
        }
    }


@app.get("/api/books")
async def get_books(email: str = Depends(require_auth)):
    """Get reading list and books"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "books": {
                "currently_reading": [
                    "The Lean Startup — Eric Ries",
                    "Fat Loss Happens on Monday — Dan John & Josh Hillis",
                    "Seeking Wisdom: From Darwin to Munger — Peter Bevelin",
                    "Tiny Habits — BJ Fogg",
                    "Reset — Chip Heath"
                ],
                "recent_reads": [
                    "A Psalm for the Wild-Built — Becky Chambers",
                    "St. Francis of Assisi — G.K. Chesterton",
                    "Chain-Gang All-Stars — Nana Kwame Adjei-Brenyah",
                    "The Diary of a CEO — Steven Bartlett"
                ],
                "up_next": [
                    "Essentialism — Greg McKeown",
                    "The Ruthless Elimination of Hurry — John Mark Comer",
                    "Slow Productivity — Cal Newport",
                    "Principles — Ray Dalio"
                ]
            }
        }
    }


@app.get("/api/principles")
async def get_principles(email: str = Depends(require_auth)):
    """Get core principles and philosophy"""
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "principles": {
                "core_beliefs": [
                    "Technology is only meaningful when it empowers people.",
                    "Data should tell a story, not just fill a dashboard.",
                    "Education scales impact better than any feature.",
                    "Curiosity beats certainty. Always."
                ],
                "tone": "Curious, clear, and constructive — blending storytelling with technical precision."
            }
        }
    }


@app.post("/api/mail")
async def send_mail(
    mail_data: MailMessage,
    email: str = Depends(require_auth)
):
    """Send an email message to Matt Deakyne"""
    # Validate message
    if not mail_data.message or len(mail_data.message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if len(mail_data.message) > 5000:
        raise HTTPException(status_code=400, detail="Message too long (max 5000 characters)")

    # Create email
    subject = f"Message from API User: {email}"

    html_body = f"""
    <html>
        <body style="font-family: 'Courier New', monospace; background-color: #0a0e14; color: #00ff00; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #1a1e24; padding: 30px; border: 2px solid #00ff00; border-radius: 8px;">
                <h1 style="color: #00ff00; margin-bottom: 20px;">New Message from Deakyne.me API</h1>

                <p style="color: #00ffff;"><strong>From:</strong> {email}</p>
                <p style="color: #00ffff;"><strong>Timestamp:</strong> {datetime.utcnow().isoformat()}</p>

                <div style="background-color: #0a0e14; padding: 20px; margin: 20px 0; border-left: 4px solid #00ff00;">
                    <p style="color: #ffff00; font-weight: bold; margin-bottom: 10px;">Message:</p>
                    <p style="color: #ffffff; white-space: pre-wrap; line-height: 1.6;">{mail_data.message}</p>
                </div>

                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #00ff00; color: #888; font-size: 12px;">
                    This message was sent via the Deakyne.me Developer API<br>
                    User email: {email}
                </p>
            </div>
        </body>
    </html>
    """

    text_body = f"""
New Message from Deakyne.me API

From: {email}
Timestamp: {datetime.utcnow().isoformat()}

Message:
{mail_data.message}

---
This message was sent via the Deakyne.me Developer API
User email: {email}
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = "mdeakyne@gmail.com"
    msg['Reply-To'] = email

    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')

    msg.attach(part1)
    msg.attach(part2)

    # Send email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"Message sent from {email} to mdeakyne@gmail.com")

        return {
            "status": "success",
            "message": "Your message has been sent to Matt Deakyne",
            "from": email
        }
    except Exception as e:
        print(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
