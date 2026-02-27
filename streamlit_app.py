"""
streamlit_app.py - Intelligent Jobseeker Engagement System UI
Run with: streamlit run ui/streamlit_app.py
"""

import streamlit as st
import requests
import json

# ─── Config ───────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="🎯 Jobseeker AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #0f3460;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .job-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .skill-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 2px 10px;
        border-radius: 20px;
        margin: 2px;
        font-size: 0.8rem;
    }
    .missing-tag {
        background: #fce4ec;
        color: #c62828;
    }
    .score-high { color: #2e7d32; font-weight: bold; }
    .score-mid  { color: #f57c00; font-weight: bold; }
    .score-low  { color: #c62828; font-weight: bold; }
    .tip-card {
        background: #f3f4f6;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 0.4rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🎯 Intelligent Jobseeker Engagement System</h1>
    <p>Personalized job recommendations • Skill gap analysis • Resume coaching</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/100/robot.png", width=80)
    st.title("Navigation")
    page = st.radio(
        "Choose a feature:",
        ["🔍 Job Recommendations", "📊 Skill Gap Analysis", "📄 Resume Coach", "💬 AI Chatbot"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**API Status**")
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        if r.status_code == 200:
            st.success("✅ Backend Connected")
        else:
            st.error("❌ Backend Error")
    except:
        st.warning("⚠️ Backend Offline\nStart: `uvicorn backend.app:app --reload`")

    st.markdown("---")
    st.caption("v1.0.0 | Powered by FastAPI + NLP")


# ─── Helper ───────────────────────────────────────────────────────────────────
def api_post(endpoint: str, payload: dict) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        st.error("Cannot connect to backend. Make sure the FastAPI server is running on port 8000.")
        return None
    except requests.HTTPError as e:
        st.error(f"API Error: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None


def score_color(pct_str: str) -> str:
    try:
        pct = int(pct_str.replace("%", ""))
        if pct >= 70: return "score-high"
        if pct >= 40: return "score-mid"
        return "score-low"
    except:
        return ""


# ─── Page: Job Recommendations ────────────────────────────────────────────────
if page == "🔍 Job Recommendations":
    st.header("🔍 Personalized Job Recommendations")
    st.write("Enter your skills and preferences to get matched jobs.")

    col1, col2 = st.columns([2, 1])

    with col1:
        input_mode = st.radio("Input Method", ["Skills List", "Resume Text"], horizontal=True)

        if input_mode == "Skills List":
            skills_input = st.text_area(
                "Your Skills (one per line or comma-separated)",
                value="Python\nDjango\nREST API\nPostgreSQL\nDocker",
                height=150,
            )
            skills_list = [s.strip() for s in skills_input.replace(",", "\n").split("\n") if s.strip()]
        else:
            resume_text = st.text_area("Paste Your Resume Text", height=200)

    with col2:
        top_n = st.slider("Results to show", 1, 10, 5)
        exp_level = st.selectbox("Experience Level", ["Any", "Junior", "Mid", "Senior"])
        location = st.text_input("Preferred Location", placeholder="Bangalore / Remote")

    if st.button("🚀 Find Jobs", use_container_width=True, type="primary"):
        with st.spinner("Finding the best matches..."):
            payload = {
                "top_n": top_n,
                "experience_level": None if exp_level == "Any" else exp_level,
                "location": location or None,
            }

            if input_mode == "Skills List":
                payload["skills"] = skills_list
                resp = api_post("/recommend", payload)
            else:
                payload["resume_text"] = resume_text
                resp = api_post("/recommend/resume", payload)

        if resp and resp.get("success"):
            data = resp["data"]
            recs = data["recommendations"]

            st.success(f"Found **{len(recs)}** jobs from {data['total_jobs_evaluated']} evaluated")

            if "detected_skills" in data:
                st.info(f"📌 Detected skills: {', '.join(data['detected_skills'])}")

            for job in recs:
                match_pct = job["match_percentage"]
                css_class = score_color(match_pct)

                st.markdown(f"""
                <div class="job-card">
                    <div style="display:flex; justify-content:space-between; align-items:center">
                        <div>
                            <h3 style="margin:0">{job['title']}</h3>
                            <p style="margin:0; color:#666">{job['company']} · {job['location']} · {job['experience_level']}</p>
                        </div>
                        <div style="text-align:right">
                            <span class="{css_class}" style="font-size:1.5rem">{match_pct}</span><br>
                            <small>Match | 💰 {job['salary_range']}</small>
                        </div>
                    </div>
                    <p style="color:#555; margin-top:0.5rem">{job['description']}</p>
                    <div>
                        <b>✅ Matched:</b> {"".join(f'<span class="skill-tag">{s}</span>' for s in job["matched_skills"])}
                    </div>
                    <div>
                        <b>📚 To Learn:</b> {"".join(f'<span class="skill-tag missing-tag">{s}</span>' for s in job["missing_skills"])}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ─── Page: Skill Gap Analysis ──────────────────────────────────────────────────
elif page == "📊 Skill Gap Analysis":
    st.header("📊 Skill Gap Analysis")
    st.write("See what skills you need for your dream role and get a learning roadmap.")

    col1, col2 = st.columns([2, 1])

    with col1:
        input_mode = st.radio("Input Method", ["Skills List", "Resume Text"], horizontal=True)
        if input_mode == "Skills List":
            skills_input = st.text_area(
                "Your Current Skills",
                value="Python\nPandas\nSQL\nStatistics",
                height=130,
            )
            user_skills = [s.strip() for s in skills_input.replace(",", "\n").split("\n") if s.strip()]
        else:
            resume_text = st.text_area("Paste Resume Text", height=180)

    with col2:
        target_role = st.selectbox(
            "Target Role",
            ["Data Scientist", "Python Developer", "Full Stack Developer",
             "DevOps Engineer", "ML Engineer", "Frontend Developer", "Custom..."]
        )
        if target_role == "Custom...":
            target_role = st.text_input("Enter custom role")

        exp_level = st.selectbox("Target Level", ["beginner", "intermediate", "advanced"])

    if st.button("🔬 Analyze Gap", use_container_width=True, type="primary"):
        with st.spinner("Analyzing your skill gap..."):
            if input_mode == "Skills List":
                payload = {"user_skills": user_skills, "target_role": target_role, "experience_level": exp_level}
                resp = api_post("/skill-gap", payload)
            else:
                payload = {"resume_text": resume_text, "target_role": target_role, "experience_level": exp_level}
                resp = api_post("/skill-gap/resume", payload)

        if resp and resp.get("success"):
            data = resp["data"]

            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Completion", data["completion_percentage"])
            c2.metric("Skills Matched", len(data["matched_skills"]))
            c3.metric("Skills Missing", len(data["missing_skills"]))
            c4.metric("Est. Time", data["estimated_learning_time"])

            st.info(f"🎯 **Readiness:** {data['readiness_assessment']}")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("### ✅ Skills You Have")
                for s in data["matched_skills"]:
                    st.markdown(f'<span class="skill-tag">{s}</span>', unsafe_allow_html=True)

            with col_b:
                st.markdown("### 📚 Skills to Learn")
                for s in data["missing_skills"]:
                    st.markdown(f'<span class="skill-tag missing-tag">{s}</span>', unsafe_allow_html=True)

            st.markdown("### 🗺️ Learning Roadmap")
            for item in data.get("prioritized_learning_path", []):
                with st.expander(f"📘 {item['skill']} ({item['priority_level'].title()})"):
                    st.write("**Resources:**")
                    for res in item["learning_resources"]:
                        st.write(f"• {res}")

            if data.get("level_breakdown"):
                st.markdown("### 📈 Level Breakdown")
                for level, info in data["level_breakdown"].items():
                    pct = info["completion"]
                    st.write(f"**{level.title()}** — {pct} complete")
                    col_x, col_y = st.columns(2)
                    with col_x:
                        st.write("Have:", ", ".join(info["matched"]) or "None")
                    with col_y:
                        st.write("Need:", ", ".join(info["missing"]) or "None")


# ─── Page: Resume Coach ────────────────────────────────────────────────────────
elif page == "📄 Resume Coach":
    st.header("📄 AI Resume Coach")
    st.write("Get instant feedback on your resume and improve your chances of landing interviews.")

    resume_text = st.text_area(
        "Paste Your Resume Text Here",
        height=250,
        placeholder="Copy and paste your complete resume text...",
    )
    target_role = st.text_input("Target Role (optional)", placeholder="e.g., Backend Developer")

    if st.button("🔍 Analyze Resume", use_container_width=True, type="primary"):
        if len(resume_text.strip()) < 50:
            st.error("Please paste your resume text (at least 50 characters).")
        else:
            with st.spinner("Analyzing your resume..."):
                payload = {"resume_text": resume_text, "target_role": target_role or None}
                resp = api_post("/resume-tips", payload)

            if resp and resp.get("success"):
                data = resp["data"]

                # Score display
                score_val = int(data["overall_score"].split("/")[0])
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Score", data["overall_score"])
                col2.metric("Grade", data["grade"].split(" - ")[0])
                col3.metric("Skills Found", len(data["detected_skills"]))

                grade_color = "#2e7d32" if score_val >= 85 else "#f57c00" if score_val >= 70 else "#c62828"
                st.markdown(f"""
                <div style="background:{grade_color}15; border-left:4px solid {grade_color};
                     padding:1rem; border-radius:8px; margin:1rem 0">
                    <b style="color:{grade_color}">{data['grade']}</b><br>{data['summary']}
                </div>
                """, unsafe_allow_html=True)

                # Detailed checks
                st.markdown("### 📋 Section-by-Section Analysis")
                for check in data["detailed_checks"]:
                    score_num = int(check["score"].split("/")[0])
                    icon = "✅" if score_num >= 8 else "⚠️" if score_num >= 6 else "❌"
                    with st.expander(f"{icon} {check['section']} — {check['score']}"):
                        st.write(check["feedback"])

                # Issues to fix
                if data["issues_to_fix"]:
                    st.markdown("### 🔧 Issues to Fix")
                    for issue in data["issues_to_fix"]:
                        st.markdown(f"""<div class="tip-card">
                            <b>{issue['section']}</b>: {issue['issue']}
                        </div>""", unsafe_allow_html=True)

                # Role-specific tips
                if data.get("role_specific_tips"):
                    st.markdown(f"### 💡 Tips for {data['target_role']}")
                    for tip in data["role_specific_tips"]:
                        st.info(f"💡 {tip}")

                # General best practices
                with st.expander("📌 General Best Practices"):
                    for practice in data["general_best_practices"]:
                        st.write(f"• {practice}")

                # Detected skills
                if data["detected_skills"]:
                    st.markdown("### 🛠️ Detected Skills")
                    st.markdown("".join(
                        f'<span class="skill-tag">{s}</span>' for s in data["detected_skills"]
                    ), unsafe_allow_html=True)


# ─── Page: AI Chatbot ─────────────────────────────────────────────────────────
elif page == "💬 AI Chatbot":
    st.header("💬 AI Jobseeker Chatbot")
    st.write("Chat with your AI assistant about jobs, skills, and career advice.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "👋 Hi! I'm your Jobseeker AI Assistant.\n\nI can help you with:\n• 🎯 Job Recommendations\n• 📊 Skill Gap Analysis\n• 📄 Resume Tips\n\nTry: 'Recommend jobs for Python developer' or 'Skill gap for Data Scientist'"}
        ]

    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about jobs, skills, or your resume..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Detect intent from text
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["recommend", "find job", "job for", "jobs"]):
            intent = "job.recommend"
            # Extract skills from prompt
            skills = [w.strip(",") for w in prompt.split() if w.istitle() and len(w) > 2]
        elif any(w in prompt_lower for w in ["skill gap", "missing skill", "what to learn", "gap"]):
            intent = "skill.gap"
            skills = []
        elif any(w in prompt_lower for w in ["resume", "cv", "application"]):
            intent = "resume.tips"
            skills = []
        else:
            intent = "default.welcome"
            skills = []

        payload = {
            "intent": intent,
            "text": prompt,
            "parameters": {"skills": skills, "role": "Software Developer"},
        }

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = api_post("/chatbot/webhook", payload)
            if resp:
                reply = resp.get("fulfillmentText", "I couldn't process that request.")
            else:
                reply = "Sorry, I'm having trouble connecting. Make sure the backend is running!"
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

    if st.button("🗑️ Clear Chat", type="secondary"):
        st.session_state.messages = []
        st.rerun()
