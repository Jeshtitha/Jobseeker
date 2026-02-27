"""
app.py - FastAPI Backend for Intelligent Jobseeker Engagement System
Member 1 | Backend + Integration Lead

Run with:
    uvicorn backend.app:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import logging
import sys
import os

# ─── Add project root to path ─────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.recommendation import get_recommendations, recommend_from_resume
from backend.skill_gap import analyze_skill_gap, analyze_gap_from_resume
from backend.resume_tips import get_resume_tips

# ─── App Setup ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="🎯 Intelligent Jobseeker Engagement API",
    description="""
## AI-Powered Jobseeker Assistant API

Provides personalized job recommendations, skill gap analysis, and resume coaching.

### Endpoints
| Endpoint | Description |
|----------|-------------|
| `POST /recommend` | Get personalized job recommendations |
| `POST /skill-gap` | Analyze skill gaps for a target role |
| `POST /resume-tips` | Get resume improvement suggestions |
| `POST /chatbot/webhook` | Dialogflow webhook for chatbot |
| `GET /health` | Health check |

### Quick Start
1. Use `/recommend` with a list of skills or resume text
2. Use `/skill-gap` with your skills and target role
3. Use `/resume-tips` with your resume text
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS Middleware (Required for frontend + chatbot integration) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # In production: restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Models (Request/Response Schemas) ───────────────────────────────

class RecommendBySkillsRequest(BaseModel):
    skills: list[str] = Field(
        ...,
        example=["Python", "Django", "REST API", "PostgreSQL"],
        description="List of user's current skills",
    )
    top_n: int = Field(5, ge=1, le=15, description="Number of recommendations to return")
    experience_level: Optional[str] = Field(None, example="Mid", description="Junior / Mid / Senior")
    location: Optional[str] = Field(None, example="Bangalore", description="Preferred location or 'Remote'")


class RecommendByResumeRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=50,
        description="Full resume text (copy-paste from your resume)",
    )
    top_n: int = Field(5, ge=1, le=15)
    experience_level: Optional[str] = None
    location: Optional[str] = None


class SkillGapBySkillsRequest(BaseModel):
    user_skills: list[str] = Field(
        ...,
        example=["Python", "Pandas", "SQL"],
        description="Current skills of the user",
    )
    target_role: str = Field(..., example="Data Scientist", description="Desired job role")
    experience_level: str = Field(
        "intermediate",
        example="intermediate",
        description="Target level: beginner | intermediate | advanced",
    )


class SkillGapByResumeRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)
    target_role: str = Field(..., example="ML Engineer")
    experience_level: str = Field("intermediate")


class ResumeTipsRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=50,
        description="Full resume text for analysis",
    )
    target_role: Optional[str] = Field(None, example="Backend Developer")


class ChatbotWebhookRequest(BaseModel):
    """Dialogflow CX/ES webhook format"""
    queryResult: Optional[dict] = None
    intentInfo: Optional[dict] = None
    sessionInfo: Optional[dict] = None
    text: Optional[str] = None  # Simplified input for direct testing


# ─── Global Exception Handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "path": str(request.url)},
    )


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Check if the API is running properly."""
    return {
        "status": "healthy",
        "service": "Intelligent Jobseeker Engagement System",
        "version": "1.0.0",
        "endpoints": ["/recommend", "/skill-gap", "/resume-tips", "/chatbot/webhook"],
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to the Jobseeker AI API 🎯",
        "docs": "/docs",
        "health": "/health",
    }


# ─── Recommendation Endpoints ─────────────────────────────────────────────────

@app.post("/recommend", tags=["Recommendations"])
def recommend_jobs(req: RecommendBySkillsRequest):
    """
    **Get personalized job recommendations based on your skills.**

    Provide your skills list and get matched jobs ranked by compatibility score.
    Each result includes matched skills, missing skills, and salary info.
    """
    try:
        logger.info(f"Recommendation request | skills={req.skills} | top_n={req.top_n}")
        result = get_recommendations(
            user_skills=req.skills,
            top_n=req.top_n,
            experience_level=req.experience_level,
            location=req.location,
        )
        return {"success": True, "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Data file missing: {e}")
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend/resume", tags=["Recommendations"])
def recommend_from_resume_endpoint(req: RecommendByResumeRequest):
    """
    **Get job recommendations by uploading/pasting your resume text.**

    Skills are automatically extracted from your resume using NLP.
    """
    try:
        logger.info("Resume-based recommendation request")
        result = recommend_from_resume(
            resume_text=req.resume_text,
            top_n=req.top_n,
            experience_level=req.experience_level,
            location=req.location,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Resume recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Skill Gap Endpoints ───────────────────────────────────────────────────────

@app.post("/skill-gap", tags=["Skill Gap Analysis"])
def skill_gap_analysis(req: SkillGapBySkillsRequest):
    """
    **Analyze your skill gap for a target role.**

    Get a detailed breakdown of what skills you have, what you're missing,
    a personalized learning roadmap, and estimated time to job-readiness.
    """
    try:
        logger.info(f"Skill gap request | role={req.target_role} | level={req.experience_level}")
        result = analyze_skill_gap(
            user_skills=req.user_skills,
            target_role=req.target_role,
            experience_level=req.experience_level,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Skill gap error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/skill-gap/resume", tags=["Skill Gap Analysis"])
def skill_gap_from_resume(req: SkillGapByResumeRequest):
    """
    **Analyze skill gaps by parsing your resume text.**

    Skills are extracted from your resume, then compared against the target role roadmap.
    """
    try:
        result = analyze_gap_from_resume(
            resume_text=req.resume_text,
            target_role=req.target_role,
            experience_level=req.experience_level,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Resume Tips Endpoint ──────────────────────────────────────────────────────

@app.post("/resume-tips", tags=["Resume Coaching"])
def resume_coaching(req: ResumeTipsRequest):
    """
    **Get AI-powered resume improvement suggestions.**

    Analysis covers: length, action verbs, quantified achievements,
    contact information, key sections, and ATS compatibility score.
    """
    try:
        logger.info(f"Resume tips request | target_role={req.target_role}")
        result = get_resume_tips(
            resume_text=req.resume_text,
            target_role=req.target_role,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Resume tips error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Chatbot Webhook ───────────────────────────────────────────────────────────

@app.post("/chatbot/webhook", tags=["Chatbot"])
async def dialogflow_webhook(request: Request):
    """
    **Dialogflow CX/ES webhook endpoint.**

    Handles intents from the Dialogflow chatbot and routes to appropriate modules.

    Supported intents:
    - `job.recommend` → Returns job recommendations
    - `skill.gap` → Returns skill gap analysis
    - `resume.tips` → Returns resume coaching
    - `default.welcome` → Welcome message
    """
    try:
        body = await request.json()
        logger.info(f"Chatbot webhook | body keys: {list(body.keys())}")

        # ── Extract intent and parameters ──────────────────────────────────
        # Support both Dialogflow ES and CX formats
        intent_name = ""
        parameters = {}

        if "queryResult" in body:
            # Dialogflow ES format
            qr = body["queryResult"]
            intent_name = qr.get("intent", {}).get("displayName", "").lower()
            parameters = qr.get("parameters", {})

        elif "intentInfo" in body:
            # Dialogflow CX format
            intent_name = body.get("intentInfo", {}).get("displayName", "").lower()
            parameters = body.get("sessionInfo", {}).get("parameters", {})

        elif "text" in body:
            # Direct test format
            intent_name = body.get("intent", "default.welcome").lower()
            parameters = body.get("parameters", {})

        logger.info(f"Intent: {intent_name} | Params: {parameters}")

        # ── Route to appropriate module ─────────────────────────────────────
        if "recommend" in intent_name or "job" in intent_name:
            skills = parameters.get("skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",")]
            result = get_recommendations(user_skills=skills, top_n=3)
            jobs = result["recommendations"]
            if jobs:
                job_list = "\n".join([
                    f"• **{j['title']}** at {j['company']} ({j['location']}) — {j['match_percentage']} match"
                    for j in jobs
                ])
                response_text = f"Here are your top job matches:\n\n{job_list}\n\nWould you like details on any of these?"
            else:
                response_text = "I couldn't find matching jobs. Try updating your skills profile!"

        elif "skill" in intent_name and "gap" in intent_name:
            user_skills = parameters.get("skills", [])
            target_role = parameters.get("role", "Software Developer")
            if isinstance(user_skills, str):
                user_skills = [s.strip() for s in user_skills.split(",")]
            result = analyze_skill_gap(user_skills, target_role)
            missing = result.get("missing_skills", [])[:5]
            pct = result.get("completion_percentage", "0%")
            response_text = (
                f"For {target_role}, you're {pct} ready!\n\n"
                f"Skills to learn next: {', '.join(missing) if missing else 'None — you are ready!'}\n\n"
                f"Estimated time: {result.get('estimated_learning_time', 'N/A')}"
            )

        elif "resume" in intent_name:
            resume_text = parameters.get("resume_text", "")
            result = get_resume_tips(resume_text)
            score = result.get("overall_score", "N/A")
            grade = result.get("grade", "N/A")
            quick_wins = result.get("quick_wins", [])[:2]
            tips_text = "\n".join([f"• {t}" for t in quick_wins]) if quick_wins else "Your resume looks good!"
            response_text = (
                f"📄 Resume Score: {score} ({grade})\n\n"
                f"Quick improvements:\n{tips_text}\n\n"
                f"Use /resume-tips API for full analysis!"
            )

        else:
            # Default welcome
            response_text = (
                "👋 Hi! I'm your Jobseeker AI Assistant.\n\n"
                "I can help you with:\n"
                "• 🎯 **Job Recommendations** — Tell me your skills\n"
                "• 📊 **Skill Gap Analysis** — Share your target role\n"
                "• 📄 **Resume Coaching** — Paste your resume text\n\n"
                "What would you like to explore?"
            )

        # ── Build Dialogflow-compatible response ────────────────────────────
        return {
            "fulfillmentResponse": {
                "messages": [{"text": {"text": [response_text]}}]
            },
            # Also include raw data for direct API callers
            "fulfillmentText": response_text,
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {
            "fulfillmentResponse": {
                "messages": [{"text": {"text": ["Sorry, I encountered an error. Please try again!"]}}]
            },
            "fulfillmentText": f"Error: {str(e)}",
        }


# ─── Run directly ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
