# Intelligent Jobseeker Engagement System

> AI-powered chatbot assistant for personalized job recommendations, skill gap analysis, and resume coaching.

---

## Architecture Overview

```
jobseeker-ai/
├─ backend/
│   ├─ app.py               ← FastAPI server (Member 1 owns this)
│   ├─ recommendation.py    ← Job recommendation engine
│   ├─ skill_gap.py         ← Skill gap analysis module
│   ├─ resume_tips.py       ← Resume coaching system
│   └─ utils/
│        └─ extract_skills.py  ← NLP skill extractor
├─ chatbot/
│   └─ dialogflow_agent/    ← Dialogflow intents config
├─ ui/
│   └─ streamlit_app.py     ← Web frontend
├─ data/
│   ├─ jobs.csv             ← Job listings dataset
│   └─ skills.json          ← Skills taxonomy + roadmaps
└─ requirements.txt


## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/recommend` | Job recommendations by skills |
| POST | `/recommend/resume` | Job recommendations by resume text |
| POST | `/skill-gap` | Skill gap analysis by skills |
| POST | `/skill-gap/resume` | Skill gap analysis by resume |
| POST | `/resume-tips` | Resume coaching and scoring |
| POST | `/chatbot/webhook` | Dialogflow webhook |

---

## Sample API Requests

### POST /recommend
```json
{
  "skills": ["Python", "Django", "REST API", "PostgreSQL"],
  "top_n": 5,
  "experience_level": "Mid",
  "location": "Bangalore"
}
```

### POST /skill-gap
```json
{
  "user_skills": ["Python", "Pandas", "SQL"],
  "target_role": "Data Scientist",
  "experience_level": "intermediate"
}
```

### POST /resume-tips
```json
{
  "resume_text": "John Doe | john@email.com ...",
  "target_role": "Backend Developer"
}
```

### POST /chatbot/webhook (Direct test format)
```json
{
  "intent": "job.recommend",
  "text": "Find jobs for Python developer",
  "parameters": {
    "skills": ["Python", "Django"],
    "role": "Python Developer"
  }
}
```

---

##  Module Details

### `extract_skills.py`
- Regex + keyword matching against `skills.json` taxonomy
- Handles aliases (ml → Machine Learning, k8s → Kubernetes)
- Returns categorized skill breakdown

### `recommendation.py`
- Loads `jobs.csv` dynamically
- Jaccard-based skill overlap scoring
- Supports experience level and location filters
- Returns match %, matched skills, missing skills

### `skill_gap.py`
- Role-specific roadmaps (6 roles built-in)
- Level-by-level breakdown (beginner/intermediate/advanced)
- Prioritized learning path with resources
- Estimated time to job-readiness

### `resume_tips.py`
- 6-dimension scoring rubric:
  - Length check
  - Impact verb usage
  - Quantified achievements
  - Contact information
  - Section completeness
  - ATS keyword density
- Grade: A-D with overall score /100
- Role-specific coaching tips

### `app.py` (FastAPI)
- CORS enabled (all origins in dev)
- Pydantic request validation
- Global error handler (no crashes)
- Dialogflow CX + ES webhook support
- Swagger UI at `/docs`

---

## 🤖 Dialogflow Integration

### Webhook URL
```
http://your-server:8000/chatbot/webhook
```

### Supported Intents
| Intent Display Name | Trigger Words | Module Called |
|--------------------|---------------|---------------|
| `job.recommend` | "recommend", "find job" | recommendation.py |
| `skill.gap` | "skill gap", "missing skills" | skill_gap.py |
| `resume.tips` | "resume", "cv" | resume_tips.py |
| `default.welcome` | (any other) | — |

