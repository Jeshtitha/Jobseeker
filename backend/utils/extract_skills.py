"""
extract_skills.py - NLP-based skill extraction from resume text
"""

import re
import json
from pathlib import Path

# Load skill taxonomy
_SKILLS_PATH = Path(__file__).parent.parent.parent / "data" / "skills.json"

def _load_all_known_skills() -> list[str]:
    """Load all skills from skills.json into a flat list."""
    with open(_SKILLS_PATH, "r") as f:
        data = json.load(f)
    all_skills = []
    for category, skills in data["skill_categories"].items():
        all_skills.extend(skills)
    return all_skills

# Compile known skills at module load
KNOWN_SKILLS = _load_all_known_skills()

# Aliases and abbreviations
SKILL_ALIASES = {
    "ml": "Machine Learning",
    "ai": "Machine Learning",
    "dl": "Deep Learning",
    "nlp": "NLP",
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "k8s": "Kubernetes",
    "tf": "TensorFlow",
    "cv": "Computer Vision",
    "ci/cd": "CI/CD",
    "rest": "REST API",
    "pg": "PostgreSQL",
    "mongo": "MongoDB",
}

def extract_skills(text: str) -> list[str]:
    """
    Extract skills from free-form text (e.g., resume, bio).
    Returns a deduplicated list of matched skills.
    """
    if not text:
        return []

    text_lower = text.lower()
    found = set()

    # Match known skills (case-insensitive)
    for skill in KNOWN_SKILLS:
        # Use word boundary matching for short skills to avoid false positives
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)

    # Match aliases
    for alias, canonical in SKILL_ALIASES.items():
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower):
            found.add(canonical)

    return sorted(found)


def extract_skills_from_resume(resume_text: str) -> dict:
    """
    Parse a resume and return structured skill information.
    Returns:
        {
            "extracted_skills": [...],
            "skill_count": N,
            "categories": { category: [skills] }
        }
    """
    with open(_SKILLS_PATH, "r") as f:
        skills_data = json.load(f)

    extracted = extract_skills(resume_text)

    # Categorize found skills
    categories = {}
    for category, skill_list in skills_data["skill_categories"].items():
        matched = [s for s in skill_list if s in extracted]
        if matched:
            categories[category] = matched

    return {
        "extracted_skills": extracted,
        "skill_count": len(extracted),
        "categories": categories,
    }


if __name__ == "__main__":
    sample = """
    Experienced Python developer with 3 years of experience.
    Proficient in Django, Flask, REST API design, PostgreSQL, and Docker.
    Familiar with Machine Learning using Scikit-learn and Pandas.
    Worked with AWS and basic CI/CD pipelines.
    """
    result = extract_skills_from_resume(sample)
    print("Extracted Skills:", result["extracted_skills"])
    print("Total:", result["skill_count"])
    print("Categories:", result["categories"])
