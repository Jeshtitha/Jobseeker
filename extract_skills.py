"""
utils/extract_skills.py
Member 2 – NLP + ML Engineer
Resume Parsing & Skill Extraction Module
"""

import re
import json
import os
from typing import Union

# ---------------------------------------------------------------------------
# Load skills knowledge-base
# ---------------------------------------------------------------------------
_SKILLS_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "skills.json")

def _load_skills_db(path: str = _SKILLS_JSON_PATH) -> dict:
    """Load skills.json; fall back to a built-in default if file not found."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Built-in fallback so the module works out-of-the-box
    return {
        "technical": [
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
            "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite",
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "XGBoost",
            "Pandas", "NumPy", "Matplotlib", "Seaborn", "Plotly",
            "Django", "Flask", "FastAPI", "React", "Vue", "Angular", "Node.js",
            "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform",
            "Git", "GitHub", "CI/CD", "Jenkins", "Linux", "Bash",
            "REST API", "GraphQL", "Microservices", "Kafka", "Spark",
            "Excel", "Tableau", "Power BI", "R", "MATLAB", "Statistics",
            "Data Analysis", "Data Engineering", "ETL", "Hadoop",
        ],
        "soft": [
            "Communication", "Leadership", "Teamwork", "Problem Solving",
            "Critical Thinking", "Time Management", "Agile", "Scrum", "Kanban",
            "Project Management", "Presentation", "Negotiation",
        ],
    }


def _clean_text(text: str) -> str:
    """Lowercase, remove special chars, normalise whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s\+\#\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_skills(
    resume_text: str,
    skills_db_path: str = _SKILLS_JSON_PATH,
    include_categories: bool = False,
) -> dict:
    """
    Extract skills from raw resume text using keyword matching
    against skills.json.

    Parameters
    ----------
    resume_text : str
        Raw text content of the resume.
    skills_db_path : str
        Path to skills.json knowledge-base.
    include_categories : bool
        If True, also return skills broken down by category.

    Returns
    -------
    dict
        {
            "skills": ["Python", "SQL", ...],               # always present
            "categorized": {"technical": [...], "soft": [...]}  # if include_categories=True
        }
    """
    if not isinstance(resume_text, str) or not resume_text.strip():
        return {"skills": [], "error": "Empty or invalid resume text provided."}

    skills_db = _load_skills_db(skills_db_path)
    cleaned = _clean_text(resume_text)

    found: dict[str, list[str]] = {}  # category -> list of matched skills

    for category, skill_list in skills_db.items():
        found[category] = []
        for skill in skill_list:
            # Build a pattern that matches whole words / phrases
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, cleaned):
                found[category].append(skill)

    all_skills = []
    for skills in found.values():
        all_skills.extend(skills)

    # Remove duplicates while preserving order
    seen = set()
    unique_skills = []
    for s in all_skills:
        if s not in seen:
            seen.add(s)
            unique_skills.append(s)

    result = {"skills": unique_skills}
    if include_categories:
        result["categorized"] = found

    return result


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_resume = """
    John Doe | john@example.com
    Summary: Experienced Data Scientist with 3 years of Python, Machine Learning,
    and SQL development. Proficient in TensorFlow, Pandas, and NumPy.
    Worked with AWS and Docker for deployment. Strong Communication and Teamwork skills.
    Education: B.Tech Computer Science | Projects: Built a Flask REST API, used Scikit-learn
    for predictive models. Familiar with Tableau and Power BI for visualisation.
    """
    result = extract_skills(sample_resume, include_categories=True)
    print(json.dumps(result, indent=2))
