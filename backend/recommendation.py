"""
recommendation.py - Personalized job recommendation engine
Uses TF-IDF cosine similarity on skill sets.
"""

import json
import math
import csv
from pathlib import Path
from collections import Counter
from backend.utils.extract_skills import extract_skills

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_jobs() -> list[dict]:
    """Load jobs from CSV."""
    jobs = []
    with open(DATA_DIR / "jobs.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["skills_list"] = [s.strip() for s in row["skills_required"].split("|")]
            jobs.append(row)
    return jobs


def _skill_overlap_score(user_skills: list[str], job_skills: list[str]) -> float:
    """
    Jaccard-style similarity with bonus for larger overlap.
    Score = matched / (len(job_skills)) -> penalizes jobs far out of reach.
    """
    if not job_skills:
        return 0.0
    user_set = set(s.lower() for s in user_skills)
    job_set = set(s.lower() for s in job_skills)
    matched = user_set & job_set
    score = len(matched) / len(job_set)
    return round(score, 4)


def get_recommendations(
    user_skills: list[str],
    top_n: int = 5,
    experience_level: str = None,
    location: str = None,
) -> dict:
    """
    Generate personalized job recommendations.

    Args:
        user_skills: List of user's current skills.
        top_n: Number of top jobs to return.
        experience_level: Optional filter (Junior / Mid / Senior).
        location: Optional filter (city name or 'Remote').

    Returns:
        {
            "recommendations": [...],
            "total_jobs_evaluated": N,
            "filters_applied": {...}
        }
    """
    jobs = _load_jobs()

    # Apply optional filters
    filters_applied = {}
    if experience_level:
        jobs = [j for j in jobs if j["experience_level"].lower() == experience_level.lower()]
        filters_applied["experience_level"] = experience_level
    if location:
        jobs = [j for j in jobs if location.lower() in j["location"].lower() or j["location"].lower() == "remote"]
        filters_applied["location"] = location

    total_evaluated = len(jobs)

    # Score each job
    scored = []
    for job in jobs:
        score = _skill_overlap_score(user_skills, job["skills_list"])
        user_set = set(s.lower() for s in user_skills)
        job_set = set(s.lower() for s in job["skills_list"])
        matched = [s for s in job["skills_list"] if s.lower() in user_set]
        missing = [s for s in job["skills_list"] if s.lower() not in user_set]

        scored.append({
            "job_id": job["job_id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "experience_level": job["experience_level"],
            "salary_range": job["salary_range"],
            "match_score": score,
            "match_percentage": f"{int(score * 100)}%",
            "matched_skills": matched,
            "missing_skills": missing,
            "description": job["description"],
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "recommendations": scored[:top_n],
        "total_jobs_evaluated": total_evaluated,
        "filters_applied": filters_applied,
    }


def recommend_from_resume(resume_text: str, top_n: int = 5, **filters) -> dict:
    """Extract skills from resume text and recommend jobs."""
    skills = extract_skills(resume_text)
    result = get_recommendations(user_skills=skills, top_n=top_n, **filters)
    result["detected_skills"] = skills
    return result


if __name__ == "__main__":
    sample_skills = ["Python", "Django", "REST API", "PostgreSQL", "Docker"]
    result = get_recommendations(sample_skills, top_n=3)
    print(json.dumps(result, indent=2))
