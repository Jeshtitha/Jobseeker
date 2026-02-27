"""
auth_page.py — Login / Register / Profile UI for JobSeeker AI
Call render_auth_page() to show the login wall.
Call render_user_menu() in the sidebar when logged in.
"""

import streamlit as st
from database import Database

_db = Database()


# ── CSS injected once ─────────────────────────────────────────────────────────

AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ── full-page auth background ── */
.auth-wrapper {
    max-width: 440px;
    margin: 40px auto 0 auto;
}
.auth-card {
    background: #ffffff;
    border: 1px solid #e2dfd9;
    border-radius: 14px;
    padding: 36px 40px 32px 40px;
    box-shadow: 0 4px 24px rgba(28,43,58,0.10);
}
.auth-logo {
    text-align: center;
    margin-bottom: 6px;
}
.auth-logo-icon {
    font-size: 2.4rem;
    line-height: 1;
}
.auth-title {
    font-family: 'IBM Plex Serif', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: #1c2b3a;
    text-align: center;
    margin-bottom: 2px;
    letter-spacing: -0.3px;
}
.auth-subtitle {
    font-size: 0.82rem;
    color: #9ca3af;
    text-align: center;
    margin-bottom: 24px;
}
.auth-divider {
    border: none;
    border-top: 1px solid #e2dfd9;
    margin: 20px 0;
}
.auth-footer {
    font-size: 0.78rem;
    color: #9ca3af;
    text-align: center;
    margin-top: 16px;
}
.auth-tag {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #2563eb;
    text-align: center;
    margin-bottom: 8px;
}
/* user chip in sidebar */
.user-chip {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 10px;
}
.user-chip-name {
    font-weight: 600;
    font-size: 0.88rem;
    color: #fff;
}
.user-chip-role {
    font-size: 0.72rem;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
</style>
"""


# ── Session helpers ───────────────────────────────────────────────────────────

def _init_session():
    """Ensure auth keys exist in st.session_state."""
    for key, default in [
        ("auth_token",    None),
        ("auth_user",     None),
        ("auth_page",     "login"),   # "login" | "register" | "profile" | "change_pw"
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def is_logged_in() -> bool:
    _init_session()
    if st.session_state.auth_token and st.session_state.auth_user:
        return True
    # Try to restore from token
    token = st.session_state.get("auth_token")
    if token:
        user = _db.validate_session(token)
        if user:
            st.session_state.auth_user = user
            return True
        # Token expired
        st.session_state.auth_token = None
        st.session_state.auth_user  = None
    return False


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def logout():
    token = st.session_state.get("auth_token")
    if token:
        _db.delete_session(token)
    st.session_state.auth_token = None
    st.session_state.auth_user  = None
    st.session_state.auth_page  = "login"


# ── Sidebar user menu ─────────────────────────────────────────────────────────

def render_user_menu():
    """Call this inside `with st.sidebar:` when user is logged in."""
    user = current_user()
    if not user:
        return
    display = user.get("full_name") or user.get("username", "User")
    st.markdown(f"""
    <div class="user-chip">
        <div class="user-chip-name">👤 {display}</div>
        <div class="user-chip-role">{user.get('role','user')}</div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Profile", use_container_width=True, key="sidebar_profile_btn"):
            st.session_state.auth_page = "profile"
            st.rerun()
    with col2:
        if st.button("Log Out", use_container_width=True, key="sidebar_logout_btn"):
            logout()
            st.rerun()


# ── Auth wall ─────────────────────────────────────────────────────────────────

def render_auth_page():
    """
    Renders the full-page login/register wall.
    Returns True if the user is now authenticated (caller should proceed to app).
    Returns False if still on auth page (caller should stop rendering).
    """
    _init_session()
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    if is_logged_in():
        return True

    # ── Header ──
    st.markdown("""
    <div class="auth-wrapper">
      <div class="auth-logo"><div class="auth-logo-icon">💼</div></div>
      <div class="auth-tag">Career Intelligence Platform</div>
      <div class="auth-title">JobSeeker AI</div>
      <div class="auth-subtitle">Your personal career growth assistant</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.session_state.auth_page

    # ────────────────────────────────────────────────────────────────────────
    # LOGIN
    # ────────────────────────────────────────────────────────────────────────
    if page == "login":
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Sign In")
            identifier = st.text_input(
                "Username or Email",
                placeholder="you@example.com",
                key="login_id",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                key="login_pw",
            )
            remember = st.checkbox("Keep me signed in", value=True)
            submitted = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

        if submitted:
            if not identifier.strip() or not password:
                st.error("Please enter your username/email and password.")
            else:
                user = _db.authenticate(identifier.strip(), password)
                if user:
                    token = _db.create_session(user["id"])
                    st.session_state.auth_token = token
                    st.session_state.auth_user  = user
                    st.success(f"Welcome back, **{user.get('full_name') or user['username']}**! 🎉")
                    st.rerun()
                else:
                    st.error("Invalid username/email or password. Please try again.")

        st.markdown('<hr class="auth-divider"/>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create an account", use_container_width=True):
                st.session_state.auth_page = "register"
                st.rerun()
        with col2:
            if st.button("Forgot password?", use_container_width=True):
                st.session_state.auth_page = "forgot"
                st.rerun()

        st.markdown('<div class="auth-footer">Secure login · Data stays on your server</div>', unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────────────────────
    # REGISTER
    # ────────────────────────────────────────────────────────────────────────
    elif page == "register":
        with st.form("register_form", clear_on_submit=False):
            st.markdown("#### Create Account")
            full_name = st.text_input("Full Name", placeholder="Jane Smith", key="reg_name")
            username  = st.text_input("Username", placeholder="janesmith", key="reg_user")
            email     = st.text_input("Email", placeholder="jane@example.com", key="reg_email")
            pw1 = st.text_input("Password", type="password", placeholder="Min 6 characters", key="reg_pw1")
            pw2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_pw2")

            submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

        if submitted:
            errors = []
            if not full_name.strip(): errors.append("Full name is required.")
            if not username.strip():  errors.append("Username is required.")
            if not email.strip():     errors.append("Email is required.")
            if not pw1:               errors.append("Password is required.")
            if pw1 != pw2:            errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    user = _db.create_user(
                        username=username.strip(),
                        email=email.strip(),
                        password=pw1,
                        full_name=full_name.strip(),
                    )
                    token = _db.create_session(user["id"])
                    st.session_state.auth_token = token
                    st.session_state.auth_user  = user
                    st.success(f"Account created! Welcome, **{full_name.strip()}**! 🎉")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        st.markdown('<hr class="auth-divider"/>', unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

    # ────────────────────────────────────────────────────────────────────────
    # FORGOT PASSWORD
    # ────────────────────────────────────────────────────────────────────────
    elif page == "forgot":
        st.markdown("#### Reset Password")
        st.info("Enter your email address. If an account exists, an admin can reset your password directly in the database, or you can update it after logging in via Profile → Change Password.")
        email_input = st.text_input("Email Address", placeholder="you@example.com", key="forgot_email")
        if st.button("Check Account", use_container_width=True, type="primary"):
            if not email_input.strip():
                st.error("Please enter your email.")
            else:
                user = _db.get_user_by_email(email_input.strip())
                if user:
                    st.success(f"Account found for **{user['username']}**. Please contact your admin to reset, or log in if you remember your password.")
                else:
                    st.warning("No account found with that email address.")

        st.markdown('<hr class="auth-divider"/>', unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

    return False   # not yet authenticated


# ── Profile page ──────────────────────────────────────────────────────────────

def render_profile_page():
    """Render the user profile & settings page (shown inside the main app)."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    user = current_user()
    if not user:
        st.error("Not logged in.")
        return

    st.markdown('<div class="auth-tag">Account</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-title" style="text-align:left;font-size:1.5rem">Profile & Settings</div>', unsafe_allow_html=True)
    st.markdown("")

    tab1, tab2 = st.tabs(["👤 Profile", "🔒 Change Password"])

    # ── Tab 1: Edit profile ──
    with tab1:
        with st.form("profile_form"):
            st.markdown("#### Update Profile")
            new_name  = st.text_input("Full Name",  value=user.get("full_name",""),  key="prof_name")
            new_email = st.text_input("Email",       value=user.get("email",""),      key="prof_email")
            st.text_input("Username", value=user.get("username",""), disabled=True,
                          help="Username cannot be changed.", key="prof_user")
            st.caption(f"Member since: {user.get('created_at','')[:10]}  ·  Last login: {(user.get('last_login') or '')[:10] or 'Now'}")
            saved = st.form_submit_button("Save Changes", use_container_width=True, type="primary")

        if saved:
            try:
                _db.update_profile(user["id"], full_name=new_name, email=new_email)
                updated = _db.get_user_by_id(user["id"])
                st.session_state.auth_user = updated
                st.success("Profile updated successfully!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    # ── Tab 2: Change password ──
    with tab2:
        with st.form("change_pw_form"):
            st.markdown("#### Change Password")
            old_pw  = st.text_input("Current Password", type="password", key="cpw_old")
            new_pw1 = st.text_input("New Password",     type="password", placeholder="Min 6 characters", key="cpw1")
            new_pw2 = st.text_input("Confirm New Password", type="password", key="cpw2")
            changed = st.form_submit_button("Update Password", use_container_width=True, type="primary")

        if changed:
            if new_pw1 != new_pw2:
                st.error("New passwords do not match.")
            else:
                try:
                    _db.change_password(user["id"], old_pw, new_pw1)
                    st.success("Password changed successfully! Please log in again.")
                    logout()
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.markdown('<hr class="auth-divider"/>', unsafe_allow_html=True)
    if st.button("← Back to Dashboard", use_container_width=False):
        st.session_state.auth_page = "login"
        st.rerun()
