"""
skill_gap.py - Skill Gap Analysis Module
Identifies missing skills and provides learning roadmaps.
"""

import json
from pathlib import Path
from backend.utils.extract_skills import extract_skills

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_skills_data() -> dict:
    with open(DATA_DIR / "skills.json") as f:
        return json.load(f)


def analyze_skill_gap(
    user_skills: list[str],
    target_role: str,
    experience_level: str = "intermediate",
) -> dict:
    """
    Analyze the skill gap between user's current skills and a target role.

    Args:
        user_skills: Skills the user currently has.
        target_role: Desired job role (e.g., "Data Scientist").
        experience_level: "beginner" | "intermediate" | "advanced"

    Returns:
        Detailed skill gap report.
    """
    skills_data = _load_skills_data()
    roadmaps = skills_data.get("skill_roadmaps", {})
    resources = skills_data.get("learning_resources", {})

    user_set = set(s.lower() for s in user_skills)

    # Find the best matching roadmap
    target_roadmap = None
    matched_role = None
    for role, roadmap in roadmaps.items():
        if role.lower() in target_role.lower() or target_role.lower() in role.lower():
            target_roadmap = roadmap
            matched_role = role
            break

    if not target_roadmap:
        # Fallback: build generic gap from all skill categories
        return _generic_gap_analysis(user_skills, target_role, skills_data)

    # Build cumulative required skills up to the requested level
    level_order = ["beginner", "intermediate", "advanced"]
    required_skills = []
    for lvl in level_order:
        required_skills.extend(target_roadmap.get(lvl, []))
        if lvl == experience_level:
            break

    required_set = set(s.lower() for s in required_skills)
    matched = [s for s in required_skills if s.lower() in user_set]
    missing = [s for s in required_skills if s.lower() not in user_set]

    completion_pct = int((len(matched) / len(required_skills)) * 100) if required_skills else 0

    # Level-by-level breakdown
    breakdown = {}
    for lvl in level_order:
        lvl_skills = target_roadmap.get(lvl, [])
        lvl_matched = [s for s in lvl_skills if s.lower() in user_set]
        lvl_missing = [s for s in lvl_skills if s.lower() not in user_set]
        breakdown[lvl] = {
            "required": lvl_skills,
            "matched": lvl_matched,
            "missing": lvl_missing,
            "completion": f"{int(len(lvl_matched)/len(lvl_skills)*100) if lvl_skills else 0}%",
        }

    # Prioritized missing skills (beginner first)
    prioritized_missing = []
    for lvl in level_order:
        for skill in breakdown[lvl]["missing"]:
            prioritized_missing.append({
                "skill": skill,
                "priority_level": lvl,
                "learning_resources": resources.get(skill, ["Search on Coursera, Udemy, or official docs"]),
            })

    # Readiness assessment
    if completion_pct >= 80:
        readiness = "High - You're well prepared for this role!"
    elif completion_pct >= 50:
        readiness = "Medium - With focused learning, you can reach this role in 3-6 months."
    elif completion_pct >= 25:
        readiness = "Low-Medium - Estimated 6-12 months of dedicated learning required."
    else:
        readiness = "Low - Significant upskilling required. Consider starting with beginner resources."

    return {
        "target_role": matched_role or target_role,
        "target_level": experience_level,
        "user_skills": user_skills,
        "required_skills": required_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "completion_percentage": f"{completion_pct}%",
        "readiness_assessment": readiness,
        "level_breakdown": breakdown,
        "prioritized_learning_path": prioritized_missing,
        "estimated_learning_time": _estimate_learning_time(len(missing)),
    }


def _estimate_learning_time(missing_count: int) -> str:
    if missing_count == 0:
        return "Ready now!"
    elif missing_count <= 2:
        return "~1-2 months"
    elif missing_count <= 4:
        return "~3-4 months"
    elif missing_count <= 6:
        return "~5-8 months"
    else:
        return "~9-12+ months"


def _generic_gap_analysis(user_skills: list[str], target_role: str, skills_data: dict) -> dict:
    """Fallback gap analysis when role not in roadmap."""
    user_set = set(s.lower() for s in user_skills)
    keywords = target_role.lower().split()

    # Collect relevant skills by keyword matching in categories
    relevant = []
    for cat, skills in skills_data["skill_categories"].items():
        if any(kw in cat for kw in keywords):
            relevant.extend(skills)

    if not relevant:
        # Return all skills as potential learning
        for cat, skills in skills_data["skill_categories"].items():
            relevant.extend(skills[:3])  # sample from each category

    missing = [s for s in relevant if s.lower() not in user_set]
    matched = [s for s in relevant if s.lower() in user_set]

    return {
        "target_role": target_role,
        "target_level": "general",
        "user_skills": user_skills,
        "required_skills": relevant,
        "matched_skills": matched,
        "missing_skills": missing,
        "completion_percentage": f"{int(len(matched)/len(relevant)*100) if relevant else 0}%",
        "readiness_assessment": "Generic analysis - no specific roadmap found for this role.",
        "level_breakdown": {},
        "prioritized_learning_path": [{"skill": s, "priority_level": "general",
                                        "learning_resources": ["Search on Coursera or Udemy"]} for s in missing[:10]],
        "estimated_learning_time": _estimate_learning_time(len(missing)),
    }


def analyze_gap_from_resume(resume_text: str, target_role: str, experience_level: str = "intermediate") -> dict:
    """Extract skills from resume and run gap analysis."""
    skills = extract_skills(resume_text)
    result = analyze_skill_gap(skills, target_role, experience_level)
    result["detected_skills"] = skills
    return result


if __name__ == "__main__":
    user_skills = ["Python", "Pandas", "SQL", "Statistics"]
    result = analyze_skill_gap(user_skills, "Data Scientist", "intermediate")
    print(json.dumps(result, indent=2))
