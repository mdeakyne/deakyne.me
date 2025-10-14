# Matt Deakyne API Specification

## Overview
**Endpoint:** `/api/matt-deakyne`  
**Description:** Returns structured data describing Matt Deakyne — a technical educator, data evangelist, and automation strategist — including professional experience, skills, projects, reading interests, and personal context.  
**Format:** `application/json`

---

## 1. Profile
```json
{
  "name": "Matthew Deakyne",
  "location": "Lawrence, Kansas",
  "email": "mdeakyne@gmail.com",
  "phone": "408-372-6366",
  "personal_brand": "People. Data. Story.",
  "headline": "Technical Educator | Data Evangelist | Automation Strategist",
  "summary": "Technologist and educator with over a decade of experience designing scalable data systems, automation frameworks, and learning programs that make complex technology approachable and impactful."
}
```

---

## 2. Professional Summary
```json
{
  "overview": "Senior leader at the intersection of education, data, and automation. Experienced in evangelism, managed services, and technical consulting across SaaS and higher education sectors.",
  "mission": "To connect people, data, and systems in ways that accelerate learning, simplify complexity, and scale understanding.",
  "core_strengths": [
    "Building scalable education frameworks and managed services programs",
    "Evangelizing complex technologies through storytelling and data visualization",
    "Designing modern analytics pipelines using Python, SQL, and automation platforms",
    "Translating customer needs into actionable product and data strategies"
  ]
}
```

---

## 3. Work Experience
```json
{
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
      "summary": "Modernized the university’s analytics ecosystem through migration of SAS to Python-based reporting.",
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
```

---

## 4. Education
```json
{
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
```

---

## 5. Technical Skills
```json
{
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
```

---

## 6. Core Competencies
```json
{
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
```

---

## 7. Projects
```json
{
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
```

---

## 8. Hobbies & Interests
```json
{
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
```

---

## 9. Reading & Learning
```json
{
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
```

---

## 10. Philosophy & Voice
```json
{
  "principles": [
    "Technology is only meaningful when it empowers people.",
    "Data should tell a story, not just fill a dashboard.",
    "Education scales impact better than any feature.",
    "Curiosity beats certainty. Always."
  ],
  "tone": "Curious, clear, and constructive — blending storytelling with technical precision."
}
```

---

## Example API Response

```json
{
  "status": "success",
  "timestamp": "2025-10-13T00:00:00Z",
  "data": {
    "profile": {...},
    "experience": {...},
    "education": {...},
    "skills": {...},
    "projects": {...},
    "hobbies": {...},
    "books": {...},
    "principles": {...}
  }
}
```
