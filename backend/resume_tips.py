"""
resume_tips.py - Resume Improvement Suggestion System
Analyzes resume text and provides actionable coaching tips.
"""

import re
import json
from pathlib import Path
from backend.utils.extract_skills import extract_skills

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_skills_data() -> dict:
    with open(DATA_DIR / "skills.json") as f:
        return json.load(f)


# ─── Scoring Rubric ──────────────────────────────────────────────────────────

def _check_length(text: str) -> dict:
    words = len(text.split())
    if words < 200:
        return {"score": 3, "issue": "Too short", "tip": "Your resume seems very brief. Aim for 400-800 words for a complete picture."}
    elif words > 1200:
        return {"score": 7, "issue": "Too long", "tip": "Your resume may be too long. Keep it concise — 1-2 pages is ideal."}
    return {"score": 10, "issue": None, "tip": "Good length! Your resume is appropriately detailed."}


def _check_impact_verbs(text: str, skills_data: dict) -> dict:
    impact_verbs = skills_data["resume_keywords"]["impact_verbs"]
    text_lower = text.lower()
    found = [v for v in impact_verbs if v.lower() in text_lower]
    missing_examples = [v for v in impact_verbs if v.lower() not in text_lower][:5]

    if len(found) < 3:
        return {
            "score": 4,
            "issue": "Weak action verbs",
            "tip": f"Use strong action verbs to describe your work. Try: {', '.join(missing_examples)}. E.g., 'Developed a REST API that served 10k+ users' instead of 'Worked on API'.",
        }
    return {
        "score": 10,
        "issue": None,
        "tip": f"Great use of action verbs! Found: {', '.join(found[:5])}",
    }


def _check_quantification(text: str) -> dict:
    # Look for numbers/metrics
    number_patterns = [
        r'\d+\s*(%|percent|users|requests|hours|days|weeks|months|years|lakh|crore|million|billion|k\b|x\b|X\b)',
        r'\$\s*\d+',
        r'₹\s*\d+',
        r'\d+\+',
    ]
    found_metrics = []
    for pattern in number_patterns:
        found_metrics.extend(re.findall(pattern, text, re.IGNORECASE))

    if not found_metrics:
        return {
            "score": 3,
            "issue": "No quantified achievements",
            "tip": "Add measurable results to your achievements! E.g., 'Reduced page load time by 40%', 'Managed a team of 5 engineers', 'Served 10,000+ daily active users'.",
        }
    elif len(found_metrics) < 3:
        return {
            "score": 7,
            "issue": "Few metrics",
            "tip": f"Good start with {len(found_metrics)} metric(s). Try to quantify more achievements for stronger impact.",
        }
    return {
        "score": 10,
        "issue": None,
        "tip": f"Excellent! {len(found_metrics)} quantified achievements found. Recruiters love numbers!",
    }


def _check_contact_info(text: str) -> dict:
    has_email = bool(re.search(r'[\w.\-]+@[\w.\-]+\.\w+', text))
    has_phone = bool(re.search(r'[\+\(]?\d[\d\s\-\(\)]{8,}', text))
    has_linkedin = bool(re.search(r'linkedin\.com|linkedin', text, re.IGNORECASE))
    has_github = bool(re.search(r'github\.com|github', text, re.IGNORECASE))

    missing = []
    if not has_email: missing.append("email")
    if not has_phone: missing.append("phone number")
    if not has_linkedin: missing.append("LinkedIn profile")
    if not has_github: missing.append("GitHub profile")

    if missing:
        return {
            "score": max(4, 10 - len(missing) * 2),
            "issue": f"Missing contact info: {', '.join(missing)}",
            "tip": f"Add your {', '.join(missing)} to make it easy for recruiters to reach you.",
        }
    return {"score": 10, "issue": None, "tip": "All key contact details present. ✓"}


def _check_sections(text: str) -> dict:
    sections = {
        "education": ["education", "degree", "university", "college", "b.tech", "b.e", "m.tech", "mba"],
        "experience": ["experience", "work history", "employment", "internship"],
        "skills": ["skills", "technical skills", "technologies"],
        "projects": ["project", "portfolio", "built", "developed"],
    }
    text_lower = text.lower()
    found_sections = []
    missing_sections = []

    for section, keywords in sections.items():
        if any(kw in text_lower for kw in keywords):
            found_sections.append(section)
        else:
            missing_sections.append(section)

    if missing_sections:
        return {
            "score": max(5, 10 - len(missing_sections) * 2),
            "issue": f"Missing sections: {', '.join(missing_sections)}",
            "tip": f"Consider adding these sections to your resume: {', '.join(missing_sections).title()}. A complete resume should have Experience, Education, Skills, and Projects.",
        }
    return {"score": 10, "issue": None, "tip": "All key sections present. ✓"}


def _check_keywords_for_ats(text: str, skills_data: dict) -> dict:
    """Check if resume contains ATS-friendly technical keywords."""
    all_skills = []
    for cat, skills in skills_data["skill_categories"].items():
        all_skills.extend(skills)

    found_skills = extract_skills(text)
    skill_count = len(found_skills)

    if skill_count < 5:
        return {
            "score": 4,
            "issue": "Low keyword density for ATS",
            "tip": "Applicant Tracking Systems (ATS) scan for keywords. List your technical skills clearly in a dedicated Skills section. Found only {} skills.".format(skill_count),
        }
    elif skill_count < 10:
        return {
            "score": 7,
            "issue": "Moderate ATS keywords",
            "tip": f"Found {skill_count} technical keywords. Try to include more relevant skills from the job description to improve ATS compatibility.",
        }
    return {
        "score": 10,
        "issue": None,
        "tip": f"Strong ATS compatibility! {skill_count} technical skills detected: {', '.join(found_skills[:8])}{'...' if len(found_skills) > 8 else ''}.",
    }


# ─── Main Function ────────────────────────────────────────────────────────────

def get_resume_tips(resume_text: str, target_role: str = None) -> dict:
    """
    Analyze resume text and return improvement suggestions.

    Args:
        resume_text: Full text of the resume.
        target_role: Optional target job role for tailored tips.

    Returns:
        Detailed coaching report.
    """
    skills_data = _load_skills_data()

    checks = {
        "length": _check_length(resume_text),
        "impact_verbs": _check_impact_verbs(resume_text, skills_data),
        "quantification": _check_quantification(resume_text),
        "contact_info": _check_contact_info(resume_text),
        "sections": _check_sections(resume_text),
        "ats_keywords": _check_keywords_for_ats(resume_text, skills_data),
    }

    # Calculate overall score
    total_score = sum(c["score"] for c in checks.values())
    max_score = len(checks) * 10
    overall_pct = int((total_score / max_score) * 100)

    if overall_pct >= 85:
        grade = "A - Excellent"
        summary = "Your resume is strong! A few minor tweaks could make it perfect."
    elif overall_pct >= 70:
        grade = "B - Good"
        summary = "Solid resume with room for improvement. Focus on the flagged areas."
    elif overall_pct >= 55:
        grade = "C - Average"
        summary = "Your resume needs work. Address the major issues to stand out."
    else:
        grade = "D - Needs Major Improvement"
        summary = "Significant improvements needed. Start with contact info and quantified achievements."

    # Collect issues and tips
    issues = []
    tips = []
    for section, check in checks.items():
        if check["issue"]:
            issues.append({"section": section.replace("_", " ").title(), "issue": check["issue"]})
        tips.append({
            "section": section.replace("_", " ").title(),
            "score": f"{check['score']}/10",
            "feedback": check["tip"],
        })

    # Role-specific tips
    role_tips = []
    if target_role:
        role_lower = target_role.lower()
        if "data" in role_lower or "ml" in role_lower or "ai" in role_lower:
            role_tips.append("Highlight any Kaggle competitions, research papers, or ML projects.")
            role_tips.append("Mention model performance metrics (accuracy, F1-score, AUC).")
        elif "frontend" in role_lower or "react" in role_lower or "ui" in role_lower:
            role_tips.append("Include links to live projects or GitHub repositories.")
            role_tips.append("Mention UI/UX tools like Figma if applicable.")
        elif "devops" in role_lower or "cloud" in role_lower:
            role_tips.append("List certifications: AWS, Azure, GCP, Kubernetes (CKA) etc.")
            role_tips.append("Mention cost savings or uptime improvements you achieved.")
        elif "backend" in role_lower or "python" in role_lower or "java" in role_lower:
            role_tips.append("Include system design experience and scale (users/requests handled).")
            role_tips.append("Mention API design patterns and database optimization experience.")

    detected_skills = extract_skills(resume_text)

    return {
        "overall_score": f"{overall_pct}/100",
        "grade": grade,
        "summary": summary,
        "target_role": target_role or "General",
        "detected_skills": detected_skills,
        "detailed_checks": tips,
        "issues_to_fix": issues,
        "role_specific_tips": role_tips,
        "quick_wins": [t["feedback"] for t in tips if int(t["score"].split("/")[0]) < 7],
        "general_best_practices": [
            "Tailor your resume to each job description using relevant keywords.",
            "Use a clean, single-column format for better ATS parsing.",
            "Keep your resume to 1 page (fresher) or 2 pages (experienced).",
            "Save and send as PDF to preserve formatting.",
            "Proofread carefully — spelling/grammar errors signal carelessness.",
        ],
    }


if __name__ == "__main__":
    sample_resume = """
    John Doe | john@email.com | +91-9876543210 | linkedin.com/in/johndoe | github.com/johndoe

    EXPERIENCE
    Software Engineer - TechCorp (2021-2024)
    - Developed REST APIs using Python and Django, serving 50,000+ daily users
    - Optimized SQL queries, reducing response time by 35%
    - Implemented CI/CD pipelines using GitHub Actions

    EDUCATION
    B.Tech Computer Science - NIT Hyderabad (2017-2021)

    SKILLS
    Python, Django, FastAPI, PostgreSQL, Docker, AWS, REST API, Git

    PROJECTS
    E-commerce Platform: Built scalable backend handling 10,000+ orders/day
    """
    result = get_resume_tips(sample_resume, "Backend Developer")
    print(json.dumps(result, indent=2))
