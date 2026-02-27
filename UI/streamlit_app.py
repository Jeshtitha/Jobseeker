
"""
streamlit_app.py — Intelligent Jobseeker Engagement System
Frontend for the FastAPI backend (backend/app.py)

Requirements:
    pip install streamlit requests pypdf2

Run:
    streamlit run streamlit_app.py
"""

import os
import io
import json
import requests
import streamlit as st
from typing import Optional

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    try:
        import pypdf as _pypdf
        PDF_SUPPORT = True
        class PdfReader:  # shim for pypdf
            def __init__(self, stream):
                self._r = _pypdf.PdfReader(stream)
            @property
            def pages(self):
                return self._r.pages
    except ImportError:
        PDF_SUPPORT = False


# ─── Page Config ──────────────────────────────────────────────────────────────
# MUST be the very first Streamlit call

st.set_page_config(
    page_title="JobSeeker AI",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #1c2b3a !important;
}
section[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.75) !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.875rem !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* ── Page background ── */
.main .block-container {
    background-color: #f7f6f3;
    padding-top: 2rem;
    max-width: 900px;
}

/* ── Page title ── */
.page-title {
    font-family: 'IBM Plex Serif', Georgia, serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #1c2b3a;
    letter-spacing: -0.3px;
    margin-bottom: 4px;
}
.page-tag {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #2563eb;
    margin-bottom: 6px;
}
.page-desc {
    font-size: 0.9rem;
    color: #6b7280;
    font-weight: 300;
    line-height: 1.7;
    margin-bottom: 1.5rem;
}

/* ── Cards ── */
.result-card {
    background: #ffffff;
    border: 1px solid #e2dfd9;
    border-radius: 10px;
    padding: 20px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(28,43,58,0.07);
}
.job-title {
    font-family: 'IBM Plex Serif', serif;
    font-size: 1rem;
    font-weight: 600;
    color: #1c2b3a;
    margin-bottom: 2px;
}
.job-meta {
    font-size: 0.8rem;
    color: #6b7280;
    margin-bottom: 8px;
}
.match-pct {
    font-family: 'IBM Plex Serif', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: #0d7377;
}

/* ── Skill tags ── */
.tag-have {
    display:inline-block; font-size:0.72rem; font-weight:500;
    font-family:'IBM Plex Mono',monospace;
    background:#f0fdf4; border:1px solid #bbf7d0; color:#166534;
    padding:2px 8px; border-radius:4px; margin:2px;
}
.tag-need {
    display:inline-block; font-size:0.72rem; font-weight:500;
    font-family:'IBM Plex Mono',monospace;
    background:#fff1f2; border:1px solid #fecdd3; color:#be123c;
    padding:2px 8px; border-radius:4px; margin:2px;
}
.tag-neutral {
    display:inline-block; font-size:0.72rem; font-weight:500;
    font-family:'IBM Plex Mono',monospace;
    background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8;
    padding:2px 8px; border-radius:4px; margin:2px;
}
.tag-amber {
    display:inline-block; font-size:0.72rem; font-weight:500;
    font-family:'IBM Plex Mono',monospace;
    background:#fffbeb; border:1px solid #fde68a; color:#b45309;
    padding:2px 8px; border-radius:4px; margin:2px;
}

/* ── Score ring wrapper ── */
.score-block {
    background:#fff; border:1px solid #e2dfd9; border-radius:10px;
    padding:20px 24px; margin-bottom:14px;
    display:flex; align-items:center; gap:20px;
}
.section-label {
    font-size:0.68rem; font-weight:600; text-transform:uppercase;
    letter-spacing:0.1em; color:#9ca3af; margin-bottom:8px;
    border-bottom:1px solid #e2dfd9; padding-bottom:6px;
}
.tip-row {
    background:#fff; border:1px solid #e2dfd9; border-left:3px solid #2563eb;
    border-radius:6px; padding:10px 14px; font-size:0.82rem;
    color:#4b5563; line-height:1.55; margin-bottom:8px;
}
.bp-row {
    font-size:0.82rem; color:#4b5563; padding:6px 0;
    border-bottom:1px solid #f3f4f6; line-height:1.55;
}
.readiness-box {
    background:#f0fafa; border:1px solid #99f6e4; border-radius:6px;
    padding:10px 14px; font-size:0.82rem; color:#0d7377;
    font-weight:500; margin-bottom:14px;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using PyPDF2 / pypdf."""
    if not PDF_SUPPORT:
        return ""
    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            parts.append(txt)
    return "\n".join(parts)


def api_post(endpoint: str, payload: dict) -> Optional[dict]:
    base = st.session_state.get("api_url", "http://localhost:8000").rstrip("/")
    try:
        resp = requests.post(f"{base}{endpoint}", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to backend at **{base}**. Make sure `uvicorn backend.app:app --reload` is running.")
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"Backend error: {detail}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
    return None


def skill_tags_html(skills: list, cls: str = "tag-neutral") -> str:
    return " ".join(f'<span class="{cls}">{s}</span>' for s in skills)


def check_health() -> bool:
    base = st.session_state.get("api_url", "http://localhost:8000").rstrip("/")
    try:
        r = requests.get(f"{base}/health", timeout=5)
        return r.ok
    except Exception:
        return False


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## JobSeeker AI")
    st.markdown("*Career Intelligence Platform*")
    st.divider()

    page = st.radio(
        "Navigation",
        options=["Overview", "Job Recommendations", "Skill Gap Analysis", "Resume Coaching", "AI Assistant"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Backend Configuration**")
    api_url = st.text_input(
        "API URL",
        value=st.session_state.get("api_url", "http://localhost:8000"),
        label_visibility="collapsed",
    )
    st.session_state["api_url"] = api_url

    if st.button("Test Connection", use_container_width=True):
        if check_health():
            st.success("Connected")
        else:
            st.error("Unreachable")

    st.divider()
    st.caption("Run backend with:\n```\nuvicorn backend.app:app --reload --port 8000\n```")


# ─── Page: Overview ───────────────────────────────────────────────────────────

if page == "Overview":
    st.markdown('<div class="page-tag">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Career Intelligence Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">An AI-powered system for job matching, skill gap analysis, and resume coaching. Select a module from the sidebar to get started.</div>', unsafe_allow_html=True)

    st.info("**Getting Started:** Ensure your FastAPI backend is running and use **Test Connection** in the sidebar to verify connectivity.")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**Job Recommendations**")
            st.markdown('<div class="page-desc" style="margin-bottom:0">Match jobs to your skills using cosine similarity scoring. Filter by experience level and location.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Resume Coaching**")
            st.markdown('<div class="page-desc" style="margin-bottom:0">ATS compatibility scored across six dimensions: length, impact verbs, quantification, contact info, sections, and keyword density.</div>', unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown("**Skill Gap Analysis**")
            st.markdown('<div class="page-desc" style="margin-bottom:0">Compare your skills against a target role roadmap. Get a prioritised learning path with estimated completion time.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**AI Assistant**")
            st.markdown('<div class="page-desc" style="margin-bottom:0">Conversational interface to the Dialogflow-compatible webhook. Supports job, skill gap, and resume intents.</div>', unsafe_allow_html=True)


# ─── Page: Job Recommendations ────────────────────────────────────────────────

elif page == "Job Recommendations":
    st.markdown('<div class="page-tag">POST /recommend &nbsp;|&nbsp; POST /recommend/resume</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Job Recommendations</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Enter your skills manually, or upload a PDF resume to have skills extracted automatically via NLP keyword matching.</div>', unsafe_allow_html=True)

    mode = st.tabs(["Enter Skills", "Upload Resume"])

    # ── Tab 1: By Skills ──
    with mode[0]:
        with st.form("rec_skills_form"):
            skills_raw = st.text_input(
                "Your Skills",
                placeholder="Python, Django, PostgreSQL, Docker, REST API",
                help="Comma-separated list of your current skills.",
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                top_n = st.number_input("Top N Results", min_value=1, max_value=15, value=5)
            with col2:
                exp_level = st.selectbox("Experience Level", ["All Levels", "Junior", "Mid", "Senior"])
            with col3:
                location = st.text_input("Location", placeholder="Bangalore, Remote")

            submitted = st.form_submit_button("Run Recommendations", use_container_width=True, type="primary")

        if submitted:
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
            if not skills:
                st.warning("Please enter at least one skill.")
            else:
                with st.spinner("Finding matching jobs…"):
                    payload = {
                        "skills": skills,
                        "top_n": int(top_n),
                        "experience_level": None if exp_level == "All Levels" else exp_level,
                        "location": location or None,
                    }
                    result = api_post("/recommend", payload)

                if result:
                    data = result.get("data", result)
                    jobs = data.get("recommendations", [])
                    total = data.get("total_jobs_evaluated", "N/A")
                    filters = data.get("filters_applied", {})

                    st.caption(f"Evaluated {total} jobs · Filters: {filters if filters else 'None'}")

                    if not jobs:
                        st.info("No matching jobs found. Try different skills or remove filters.")
                    else:
                        for job in jobs:
                            matched = job.get("matched_skills", [])
                            missing = job.get("missing_skills", [])
                            pct     = job.get("match_percentage", "—")

                            with st.container(border=True):
                                c1, c2 = st.columns([4, 1])
                                with c1:
                                    st.markdown(f'<div class="job-title">{job.get("title","Unknown Role")}</div>', unsafe_allow_html=True)
                                    meta = " · ".join(filter(None, [job.get("company",""), job.get("location",""), job.get("experience_level","")]))
                                    st.markdown(f'<div class="job-meta">{meta}</div>', unsafe_allow_html=True)
                                    if matched:
                                        st.markdown(skill_tags_html(matched[:5], "tag-have"), unsafe_allow_html=True)
                                    if missing:
                                        st.markdown(skill_tags_html(missing[:4], "tag-need"), unsafe_allow_html=True)
                                    if job.get("salary_range"):
                                        st.caption(f"Salary: {job['salary_range']}")
                                with c2:
                                    st.markdown(f'<div class="match-pct">{pct}</div><div style="font-size:0.65rem;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em">Match</div>', unsafe_allow_html=True)

    # ── Tab 2: By Resume PDF ──
    with mode[1]:
        if not PDF_SUPPORT:
            st.warning("PDF parsing requires PyPDF2 or pypdf. Install with: `pip install pypdf2`")

        uploaded = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf", "txt", "doc"],
            help="Upload your resume. Text will be extracted and skills identified automatically.",
            key="rec_resume_upload",
        )

        if uploaded:
            file_bytes = uploaded.read()
            if uploaded.type == "application/pdf":
                resume_text = extract_text_from_pdf(file_bytes)
                if not resume_text.strip():
                    st.warning("Could not extract text from this PDF. The file may be scanned/image-based. Try a text-based PDF.")
                else:
                    st.success(f"Extracted {len(resume_text.split())} words from **{uploaded.name}**")
            else:
                resume_text = file_bytes.decode("utf-8", errors="replace")
                st.success(f"Loaded **{uploaded.name}** ({len(resume_text.split())} words)")

            with st.form("rec_resume_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    top_n2 = st.number_input("Top N Results", min_value=1, max_value=15, value=5, key="rn2")
                with col2:
                    exp_level2 = st.selectbox("Experience Level", ["All Levels", "Junior", "Mid", "Senior"], key="el2")
                with col3:
                    location2 = st.text_input("Location", placeholder="Bangalore, Remote", key="loc2")

                submitted2 = st.form_submit_button("Extract Skills & Recommend", use_container_width=True, type="primary")

            if submitted2:
                if not resume_text.strip() or len(resume_text.strip()) < 50:
                    st.warning("Could not extract enough text from the uploaded file.")
                else:
                    with st.spinner("Extracting skills and finding jobs…"):
                        payload = {
                            "resume_text": resume_text,
                            "top_n": int(top_n2),
                            "experience_level": None if exp_level2 == "All Levels" else exp_level2,
                            "location": location2 or None,
                        }
                        result = api_post("/recommend/resume", payload)

                    if result:
                        data     = result.get("data", result)
                        jobs     = data.get("recommendations", [])
                        detected = data.get("detected_skills", [])
                        total    = data.get("total_jobs_evaluated", "N/A")

                        if detected:
                            st.markdown("**Detected Skills**")
                            st.markdown(skill_tags_html(detected, "tag-neutral"), unsafe_allow_html=True)
                            st.markdown("")

                        st.caption(f"Evaluated {total} jobs")

                        if not jobs:
                            st.info("No matching jobs found.")
                        else:
                            for job in jobs:
                                matched = job.get("matched_skills", [])
                                missing = job.get("missing_skills", [])
                                pct     = job.get("match_percentage", "—")

                                with st.container(border=True):
                                    c1, c2 = st.columns([4, 1])
                                    with c1:
                                        st.markdown(f'<div class="job-title">{job.get("title","Unknown Role")}</div>', unsafe_allow_html=True)
                                        meta = " · ".join(filter(None, [job.get("company",""), job.get("location",""), job.get("experience_level","")]))
                                        st.markdown(f'<div class="job-meta">{meta}</div>', unsafe_allow_html=True)
                                        if matched:
                                            st.markdown(skill_tags_html(matched[:5], "tag-have"), unsafe_allow_html=True)
                                        if missing:
                                            st.markdown(skill_tags_html(missing[:4], "tag-need"), unsafe_allow_html=True)
                                        if job.get("salary_range"):
                                            st.caption(f"Salary: {job['salary_range']}")
                                    with c2:
                                        st.markdown(f'<div class="match-pct">{pct}</div><div style="font-size:0.65rem;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em">Match</div>', unsafe_allow_html=True)
        else:
            st.info("Upload a PDF or TXT resume file to continue.")


# ─── Page: Skill Gap Analysis ─────────────────────────────────────────────────

elif page == "Skill Gap Analysis":
    st.markdown('<div class="page-tag">POST /skill-gap &nbsp;|&nbsp; POST /skill-gap/resume</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Skill Gap Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Identify missing skills for a target role using the roadmap in <code>skills.json</code>. Outputs a prioritised learning path with estimated time to readiness.</div>', unsafe_allow_html=True)

    def render_gap_result(data: dict):
        matched  = data.get("matched_skills", [])
        missing  = data.get("missing_skills", [])
        pct      = data.get("completion_percentage", "0%")
        time_est = data.get("estimated_learning_time", "N/A")
        readiness= data.get("readiness_assessment", "")
        path     = data.get("prioritized_learning_path", [])
        detected = data.get("detected_skills", [])
        role     = data.get("target_role", "")
        level    = data.get("target_level", "")

        if detected:
            st.markdown("**Skills Detected from Resume**")
            st.markdown(skill_tags_html(detected, "tag-neutral"), unsafe_allow_html=True)
            st.divider()

        c1, c2, c3 = st.columns(3)
        pct_num = int(pct.replace("%","")) if "%" in str(pct) else 0
        with c1:
            st.metric("Job Readiness", pct)
        with c2:
            st.metric("Skills Matched", len(matched))
        with c3:
            st.metric("Skills Missing", len(missing))

        st.progress(pct_num / 100, text=f"{pct} ready for {role} ({level})")

        if readiness:
            st.markdown(f'<div class="readiness-box">{readiness}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if matched:
                st.markdown('<div class="section-label">Skills You Have</div>', unsafe_allow_html=True)
                st.markdown(skill_tags_html(matched, "tag-have"), unsafe_allow_html=True)
        with col2:
            if missing:
                st.markdown('<div class="section-label">Skills to Acquire</div>', unsafe_allow_html=True)
                st.markdown(skill_tags_html(missing, "tag-amber"), unsafe_allow_html=True)

        if path:
            st.markdown("")
            st.markdown(f'<div class="section-label">Prioritised Learning Path &mdash; Est. {time_est}</div>', unsafe_allow_html=True)

            table_rows = []
            for i, item in enumerate(path, 1):
                if isinstance(item, str):
                    skill, lvl, resource = item, "general", ""
                else:
                    skill    = item.get("skill", "")
                    lvl      = item.get("priority_level", "general")
                    res_list = item.get("learning_resources", [])
                    resource = res_list[0] if res_list else ""
                table_rows.append({"#": i, "Skill": skill, "Level": lvl.title(), "Resource": resource})

            st.dataframe(
                table_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "#":        st.column_config.NumberColumn(width="small"),
                    "Skill":    st.column_config.TextColumn(width="medium"),
                    "Level":    st.column_config.TextColumn(width="small"),
                    "Resource": st.column_config.TextColumn(width="large"),
                },
            )

    mode = st.tabs(["Enter Skills", "Upload Resume"])

    # ── Tab 1: By Skills ──
    with mode[0]:
        with st.form("gap_skills_form"):
            skills_raw = st.text_input(
                "Your Current Skills",
                placeholder="Python, Pandas, SQL, NumPy, Statistics",
                help="Comma-separated list of skills you currently have.",
            )
            col1, col2 = st.columns(2)
            with col1:
                target_role = st.text_input("Target Role", placeholder="e.g. Data Scientist, ML Engineer")
            with col2:
                gap_level = st.selectbox("Target Level", ["beginner", "intermediate", "advanced"], index=1)

            submitted = st.form_submit_button("Analyse Skill Gap", use_container_width=True, type="primary")

        if submitted:
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
            if not skills:
                st.warning("Please enter at least one skill.")
            elif not target_role.strip():
                st.warning("Please enter a target role.")
            else:
                with st.spinner("Analysing skill gap…"):
                    payload = {"user_skills": skills, "target_role": target_role.strip(), "experience_level": gap_level}
                    result  = api_post("/skill-gap", payload)
                if result:
                    render_gap_result(result.get("data", result))

    # ── Tab 2: By Resume PDF ──
    with mode[1]:
        if not PDF_SUPPORT:
            st.warning("PDF parsing requires PyPDF2 or pypdf. Install with: `pip install pypdf2`")

        uploaded = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf", "txt", "doc"],
            help="Upload your resume. Skills will be extracted and compared against the role roadmap.",
            key="gap_resume_upload",
        )

        if uploaded:
            file_bytes = uploaded.read()
            if uploaded.type == "application/pdf":
                resume_text = extract_text_from_pdf(file_bytes)
                if not resume_text.strip():
                    st.warning("Could not extract text from this PDF. Try a text-based PDF.")
                else:
                    st.success(f"Extracted {len(resume_text.split())} words from **{uploaded.name}**")
            else:
                resume_text = file_bytes.decode("utf-8", errors="replace")
                st.success(f"Loaded **{uploaded.name}** ({len(resume_text.split())} words)")

            with st.form("gap_resume_form"):
                col1, col2 = st.columns(2)
                with col1:
                    target_role2 = st.text_input("Target Role", placeholder="e.g. ML Engineer, Backend Developer", key="tr2")
                with col2:
                    gap_level2 = st.selectbox("Target Level", ["beginner", "intermediate", "advanced"], index=1, key="gl2")

                submitted2 = st.form_submit_button("Extract Skills & Analyse Gap", use_container_width=True, type="primary")

            if submitted2:
                if not resume_text.strip() or len(resume_text.strip()) < 50:
                    st.warning("Could not extract enough text from the uploaded file.")
                elif not target_role2.strip():
                    st.warning("Please enter a target role.")
                else:
                    with st.spinner("Extracting skills and analysing gap…"):
                        payload = {"resume_text": resume_text, "target_role": target_role2.strip(), "experience_level": gap_level2}
                        result  = api_post("/skill-gap/resume", payload)
                    if result:
                        render_gap_result(result.get("data", result))
        else:
            st.info("Upload a PDF or TXT resume file to continue.")


# ─── Page: Resume Coaching ────────────────────────────────────────────────────

elif page == "Resume Coaching":
    st.markdown('<div class="page-tag">POST /resume-tips</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Resume Coaching</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Upload your resume to receive a detailed ATS compatibility report. Scored across six dimensions with actionable feedback, role-specific tips, and best practices.</div>', unsafe_allow_html=True)

    if not PDF_SUPPORT:
        st.warning("PDF parsing requires PyPDF2 or pypdf. Install with: `pip install pypdf2`")

    # ── File upload ──
    uploaded = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf", "txt", "doc"],
        help="Upload your resume as PDF or plain text. The text will be extracted and analysed.",
        key="tips_resume_upload",
    )

    resume_text = ""
    word_count  = 0

    if uploaded:
        file_bytes = uploaded.read()
        if uploaded.type == "application/pdf":
            resume_text = extract_text_from_pdf(file_bytes)
            if not resume_text.strip():
                st.warning("Could not extract text from this PDF. It may be a scanned image. Please use a text-based PDF.")
            else:
                word_count = len(resume_text.split())
                st.success(f"Extracted **{word_count} words** from **{uploaded.name}**")
        else:
            resume_text = file_bytes.decode("utf-8", errors="replace")
            word_count  = len(resume_text.split())
            st.success(f"Loaded **{uploaded.name}** — {word_count} words")
    else:
        st.info("Upload a PDF or TXT resume file to begin analysis.")

    target_role = st.text_input(
        "Target Role (optional)",
        placeholder="e.g. Backend Developer, Data Scientist",
        help="Providing a target role enables role-specific coaching tips.",
    )

    run_btn = st.button(
        "Analyse Resume",
        type="primary",
        use_container_width=True,
        disabled=(not resume_text.strip() or word_count < 30),
    )

    if run_btn:
        with st.spinner("Analysing resume…"):
            payload = {
                "resume_text": resume_text,
                "target_role": target_role.strip() or None,
            }
            result = api_post("/resume-tips", payload)

        if result:
            data = result.get("data", result)

            score_raw = data.get("overall_score", "0/100")
            score_num = int(str(score_raw).split("/")[0]) if "/" in str(score_raw) else int(score_raw or 0)
            grade     = data.get("grade",   "")
            summary   = data.get("summary", "")
            role_out  = data.get("target_role", "General")
            detected  = data.get("detected_skills", [])
            checks    = data.get("detailed_checks", [])
            quick_wins= data.get("quick_wins", [])
            role_tips = data.get("role_specific_tips", [])
            bps       = data.get("general_best_practices", [])

            # ── Score row ──
            c1, c2, c3 = st.columns([1.2, 2, 2])
            with c1:
                color = "#166534" if score_num >= 70 else "#b45309" if score_num >= 55 else "#be123c"
                st.markdown(f"""
                <div style="text-align:center;background:#fff;border:1px solid #e2dfd9;border-radius:10px;padding:20px 10px">
                    <div style="font-family:'IBM Plex Serif',serif;font-size:2.4rem;font-weight:700;color:{color};line-height:1">{score_num}</div>
                    <div style="font-size:0.75rem;color:#9ca3af;margin-top:2px">/ 100</div>
                    <div style="font-size:0.8rem;font-weight:600;color:#1c2b3a;margin-top:8px">{grade.split(" - ")[1] if " - " in grade else grade}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{grade}**")
                st.markdown(f'<div style="font-size:0.88rem;color:#4b5563;line-height:1.6">{summary}</div>', unsafe_allow_html=True)
                st.caption(f"Target Role: {role_out}")
            with c3:
                if detected:
                    st.markdown("**Detected Skills**")
                    st.markdown(skill_tags_html(detected[:10], "tag-neutral"), unsafe_allow_html=True)
                    if len(detected) > 10:
                        st.caption(f"+{len(detected)-10} more skills detected")

            st.markdown("")

            # ── Detailed checks table ──
            if checks:
                st.markdown('<div class="section-label">Detailed Check Results</div>', unsafe_allow_html=True)
                rows = []
                for c in checks:
                    rows.append({
                        "Section":  c.get("section", ""),
                        "Score":    c.get("score", ""),
                        "Feedback": c.get("feedback", ""),
                    })
                st.dataframe(
                    rows,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Section":  st.column_config.TextColumn(width="small"),
                        "Score":    st.column_config.TextColumn(width="small"),
                        "Feedback": st.column_config.TextColumn(width="large"),
                    },
                )
                st.markdown("")

            # ── Quick wins / issues ──
            if quick_wins:
                st.markdown('<div class="section-label">Issues to Address</div>', unsafe_allow_html=True)
                for tip in quick_wins:
                    st.markdown(f'<div class="tip-row">{tip}</div>', unsafe_allow_html=True)
                st.markdown("")

            # ── Role-specific tips ──
            if role_tips:
                st.markdown(f'<div class="section-label">Role-Specific Tips &mdash; {role_out}</div>', unsafe_allow_html=True)
                for tip in role_tips:
                    st.markdown(f'<div class="tip-row" style="border-left-color:#0d7377">{tip}</div>', unsafe_allow_html=True)
                st.markdown("")

            # ── Best practices ──
            if bps:
                st.markdown('<div class="section-label">General Best Practices</div>', unsafe_allow_html=True)
                for bp in bps:
                    st.markdown(f'<div class="bp-row">&#8226; {bp}</div>', unsafe_allow_html=True)


# ─── Page: AI Assistant ───────────────────────────────────────────────────────

elif page == "AI Assistant":
    import streamlit.components.v1 as components

    st.markdown('<div class="page-tag">Dialogflow Messenger &nbsp;|&nbsp; Webhook Chat</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">AI Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Two ways to chat: use the embedded <b>Dialogflow Messenger</b> widget (Tab 1) powered by your Google Dialogflow ES agent, or use the <b>Webhook Chat</b> (Tab 2) which calls your FastAPI backend directly.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Dialogflow Messenger", "🔗 Webhook Chat"])

    # ── Tab 1: Dialogflow Messenger (proper embed via st.components.html) ──
    with tab1:
        st.markdown(
            "The chat widget below is powered by your **Dialogflow ES** agent. "
            "Click the chat bubble at the bottom-right to open it.",
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------ #
        # Replace the values below with YOUR agent's details from:            #
        #   Dialogflow ES Console → Integrations → Dialogflow Messenger       #
        #   → Enable → Copy embed code                                        #
        # ------------------------------------------------------------------ #
        DIALOGFLOW_PROJECT_ID = "jobseekerbot-iqqu"   # ← your GCP project ID
        DIALOGFLOW_AGENT_ID   = "488e6200-2739-4dca-9b02-067d183a7210"  # ← agent/cx ID
        CHAT_TITLE            = "JobSeeker AI"

        dialogflow_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8"/>
          <style>
            html, body {{
              margin: 0; padding: 0;
              height: 600px;
              background: #f7f6f3;
              font-family: 'IBM Plex Sans', sans-serif;
            }}
            df-messenger {{
              --df-messenger-bot-message: #1c2b3a;
              --df-messenger-button-titlebar-color: #1c2b3a;
              --df-messenger-chat-background-color: #f7f6f3;
              --df-messenger-font-color: white;
              --df-messenger-send-icon: #0d7377;
              --df-messenger-user-message: #0d7377;
              z-index: 999;
              position: fixed;
              bottom: 16px;
              right: 16px;
            }}
          </style>
          <!-- Dialogflow ES Messenger script -->
          <script src="https://www.gstatic.com/dialogflow-console/fast/messenger/bootstrap.js?v=1"></script>
        </head>
        <body>
          <div style="padding:20px;">
            <h3 style="color:#1c2b3a;font-family:'IBM Plex Serif',serif;margin-bottom:8px;">
              💼 {CHAT_TITLE}
            </h3>
            <p style="color:#6b7280;font-size:0.9rem;line-height:1.6;">
              Your Dialogflow agent is ready. Click the <strong>chat icon</strong> 
              at the bottom-right corner to start a conversation.<br/><br/>
              Try asking:<br/>
              &bull; <em>"Find jobs for a Python developer"</em><br/>
              &bull; <em>"Skill gap for Data Scientist"</em><br/>
              &bull; <em>"Give me resume tips"</em>
            </p>
          </div>

          <!-- Dialogflow ES Messenger Widget -->
          <df-messenger
            intent="WELCOME"
            chat-title="{CHAT_TITLE}"
            agent-id="{DIALOGFLOW_AGENT_ID}"
            language-code="en"
          ></df-messenger>
        </body>
        </html>
        """

        components.html(dialogflow_html, height=620, scrolling=False)

        st.info(
            "**Setup:** If the chat bubble doesn't appear, go to your "
            "[Dialogflow ES Console](https://dialogflow.cloud.google.com/) → "
            "**Integrations** → **Dialogflow Messenger** → Enable and copy your `agent-id`. "
            "Then update `DIALOGFLOW_AGENT_ID` in this file.",
            icon=None,
        )

    # ── Tab 2: Webhook Chat (calls FastAPI backend directly) ──
    with tab2:
        st.markdown(
            "This chat calls your **FastAPI backend** webhook directly at "
            "`/chatbot/webhook`. Make sure the backend is running.",
        )

        # Session state for chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": (
                        "Hello! I'm your JobSeeker AI Assistant.\n\n"
                        "I can help you with:\n"
                        "- 💼 Job recommendations based on your skills\n"
                        "- 📊 Skill gap analysis for a target role\n"
                        "- 📝 Resume coaching and ATS scoring\n\n"
                        "How can I help you today?"
                    ),
                }
            ]

        # Quick-action buttons
        col1, col2, col3, col4 = st.columns(4)
        quick_sent = None
        with col1:
            if st.button("🐍 Python developer jobs", use_container_width=True):
                quick_sent = "Find jobs for a Python developer"
        with col2:
            if st.button("📊 Data Scientist gap", use_container_width=True):
                quick_sent = "Skill gap analysis for Data Scientist"
        with col3:
            if st.button("📝 Resume tips", use_container_width=True):
                quick_sent = "Give me resume tips"
        with col4:
            if st.button("🤖 ML Engineer skills", use_container_width=True):
                quick_sent = "What skills do I need for ML Engineer?"

        # Render chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        def detect_intent(text: str) -> str:
            t = text.lower()
            if any(w in t for w in ["job", "recommend", "find", "match", "developer", "engineer"]):
                return "job.recommend"
            if "gap" in t or ("skill" in t and ("need" in t or "miss" in t)):
                return "skill.gap"
            if "resume" in t or " cv" in t or "ats" in t or "tips" in t:
                return "resume.tips"
            return "default.welcome"

        def extract_params(text: str) -> dict:
            import re
            p = {}
            m = re.search(
                r"for\s+((?:[A-Z][a-z]+\s?)+(?:Engineer|Developer|Scientist|Analyst|Designer|Manager|Lead|Architect))",
                text, re.I,
            )
            if m:
                p["role"] = m.group(1).strip()
            skills_m = re.findall(r"\b([A-Z][a-zA-Z+#]+(?:\.[a-z]+)?)\b", text)
            if skills_m:
                p["skills"] = ", ".join(skills_m[:5])
            return p

        def send_message(user_text: str):
            st.session_state.chat_history.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.markdown(user_text)

            with st.chat_message("assistant"):
                with st.spinner("Processing…"):
                    payload = {
                        "text":       user_text,
                        "intent":     detect_intent(user_text),
                        "parameters": extract_params(user_text),
                    }
                    base = st.session_state.get("api_url", "http://localhost:8000").rstrip("/")
                    try:
                        resp = requests.post(f"{base}/chatbot/webhook", json=payload, timeout=30)
                        resp.raise_for_status()
                        data  = resp.json()
                        reply = (
                            data.get("fulfillmentText")
                            or (data.get("fulfillmentResponse", {})
                                   .get("messages", [{}])[0]
                                   .get("text", {})
                                   .get("text", [""])[0])
                            or "No response from server."
                        )
                    except Exception as e:
                        reply = (
                            f"⚠️ Could not reach the backend at `{base}`.\n\n"
                            f"Make sure `uvicorn backend.app:app --reload` is running.\n\n"
                            f"**Error:** {e}"
                        )

                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

        # Handle quick action
        if quick_sent:
            send_message(quick_sent)
            st.rerun()

        # Chat input
        user_input = st.chat_input("Type a message… e.g. 'Find Python developer jobs'")
        if user_input:
            send_message(user_input)

        # Clear chat
        if st.button("🗑️ Clear conversation", use_container_width=False):
            st.session_state.chat_history = [st.session_state.chat_history[0]]
            st.rerun()
