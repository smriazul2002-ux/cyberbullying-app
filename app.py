import streamlit as st
st.set_page_config(page_title="Cyberbullying Pro", layout="centered", page_icon="🛡️")

import pickle
import re
import string
import os
import html
import pyrebase
import pandas as pd
import plotly.graph_objects as go
import datetime
import time
from textblob import TextBlob
from wordcloud import WordCloud
from fpdf import FPDF
from cryptography.fernet import Fernet
import random

from utils import (
    clean_text,
    check_bangla_toxic,
    password_strength,
    highlight_text,
    extract_youtube_video_id,
)

# 🎨 STYLE
st.markdown("""
<style>
.main { background-color: #0e1117; }
h1 { text-align: center; }
.block-container { padding-top: 2rem; }
.stTextArea textarea { border-radius: 12px; }
.stButton>button {
    width:100%;
    border-radius:10px;
    height:3em;
    background-color: #6C63FF;
    color: white;
    border: none;
    font-weight: 500;
    transition: 0.2s;
}
.stButton>button:hover {
    background-color: #5a52d5;
    transform: translateY(-1px);
}
.post-card {
    background: #1a1c24;
    border: 1px solid #2c2f3a;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 18px;
}
.post-header {
    font-size: 15px;
    color: #a0a3b1;
    margin-bottom: 4px;
}
.post-text {
    font-size: 17px;
    color: #f1f1f3;
    margin-bottom: 10px;
}
.badge-safe {
    background-color: #163a2b;
    color: #4ade80;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    display: inline-block;
    margin-right: 8px;
}
.badge-bully {
    background-color: #3a1616;
    color: #f87171;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    display: inline-block;
    margin-right: 8px;
}
.badge-sentiment-pos {
    background-color: #163a2b;
    color: #4ade80;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    display: inline-block;
}
.badge-sentiment-neg {
    background-color: #3a1616;
    color: #f87171;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    display: inline-block;
}
.badge-sentiment-neu {
    background-color: #2c2f3a;
    color: #a0a3b1;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    display: inline-block;
}
.metric-box {
    background: #1a1c24;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    border: 1px solid #2c2f3a;
}
.metric-number {
    font-size: 26px;
    font-weight: 600;
    color: #f1f1f3;
}
.metric-label {
    font-size: 13px;
    color: #a0a3b1;
}
mark {
    background-color: #f87171;
    color: #3a1616;
    padding: 1px 4px;
    border-radius: 4px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# 🔥 FIREBASE CONFIG (loaded from .streamlit/secrets.toml -- never hardcode secrets in source code)
firebase_config = {
    "apiKey": st.secrets["firebase"]["apiKey"],
    "authDomain": st.secrets["firebase"]["authDomain"],
    "databaseURL": st.secrets["firebase"]["databaseURL"],
    "projectId": st.secrets["firebase"]["projectId"],
    "storageBucket": st.secrets["firebase"]["storageBucket"],
    "messagingSenderId": st.secrets["firebase"]["messagingSenderId"],
    "appId": st.secrets["firebase"]["appId"],
}

ADMIN_EMAIL = st.secrets["app"]["admin_email"]

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

# 🔒 ENCRYPTION SETUP (post text is encrypted before being stored in Firebase)
BASE_DIR = os.path.dirname(__file__)
KEY_FILE = os.path.join(BASE_DIR, "secret.key")

def load_or_create_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

fernet = Fernet(load_or_create_key())

def encrypt_text(plain_text):
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_text(token):
    try:
        return fernet.decrypt(token.encode()).decode()
    except Exception:
        # Legacy posts stored before encryption was added -- show as-is
        return token

# ⏱️ RATE LIMITING CONFIG
RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW = 60  # seconds

if "submission_times" not in st.session_state:
    st.session_state.submission_times = []

def check_rate_limit():
    now = time.time()
    st.session_state.submission_times = [
        t for t in st.session_state.submission_times if now - t < RATE_LIMIT_WINDOW
    ]
    if len(st.session_state.submission_times) >= RATE_LIMIT_COUNT:
        return False
    st.session_state.submission_times.append(now)
    return True

# 📝 AUDIT LOG
def log_audit(action, details=""):
    try:
        db.child("audit_log").push({
            "user": st.session_state.get("user_email", "unknown"),
            "action": action,
            "details": details,
            "time": str(datetime.datetime.now())
        })
    except Exception:
        pass  # never let logging failures break the app

def get_token():
    """Return the current session's Firebase ID token, required for
    database operations under the tightened Firebase security rules
    (see firebase_rules_hardened.json)."""
    return st.session_state.get("id_token")

# 🚩 REPORT / 🚫 BLOCK USER FUNCTIONS
def report_post(post_id, reported_user, reason):
    db.child("reports").push({
        "post_id": post_id,
        "reported_user": reported_user,
        "reported_by": st.session_state.user_email,
        "reason": reason,
        "time": str(datetime.datetime.now())
    }, get_token())
    log_audit("post_reported", f"{reported_user} | post {post_id}")

def block_user(blocked_email):
    key = _safe_key(st.session_state.user_email)
    db.child("blocked_users").child(key).child(_safe_key(blocked_email)).set(True, get_token())
    log_audit("user_blocked", blocked_email)

def unblock_user(blocked_email):
    key = _safe_key(st.session_state.user_email)
    db.child("blocked_users").child(key).child(_safe_key(blocked_email)).remove(get_token())
    log_audit("user_unblocked", blocked_email)

def get_blocked_users():
    key = _safe_key(st.session_state.user_email)
    data = db.child("blocked_users").child(key).get(get_token()).val()
    return list(data.keys()) if data else []

def is_blocked(email, blocked_list):
    return _safe_key(email) in blocked_list

# 🔒 BRUTE-FORCE LOGIN PROTECTION
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def _safe_key(email):
    return email.replace(".", "_").replace("@", "_at_")

def get_login_attempts(email):
    data = db.child("login_attempts").child(_safe_key(email)).get().val()
    return data or {"count": 0, "locked_until": None}

def record_failed_attempt(email):
    attempts = get_login_attempts(email)
    count = attempts.get("count", 0) + 1
    update = {"count": count, "last_attempt": str(datetime.datetime.now())}
    if count >= MAX_FAILED_ATTEMPTS:
        locked_until = datetime.datetime.now() + datetime.timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update["locked_until"] = str(locked_until)
    db.child("login_attempts").child(_safe_key(email)).update(update)

def reset_login_attempts(email):
    db.child("login_attempts").child(_safe_key(email)).remove()

def is_locked_out(email):
    attempts = get_login_attempts(email)
    locked_until = attempts.get("locked_until")
    if locked_until:
        try:
            locked_until_dt = datetime.datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S.%f")
            if datetime.datetime.now() < locked_until_dt:
                remaining = (locked_until_dt - datetime.datetime.now()).seconds // 60 + 1
                return True, remaining
        except Exception:
            pass
    return False, 0

# ⏳ SESSION TIMEOUT (auto-logout after inactivity)
SESSION_TIMEOUT_MINUTES = 15

def check_session_timeout():
    if st.session_state.get("logged_in"):
        elapsed = time.time() - st.session_state.get("last_activity", time.time())
        if elapsed > SESSION_TIMEOUT_MINUTES * 60:
            log_audit("auto_logout", "Session expired due to inactivity")
            st.session_state.logged_in = False
            st.warning("⏳ Your session expired due to inactivity. Please log in again.")
            st.stop()
        else:
            st.session_state.last_activity = time.time()

# 🔐 SESSION
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "last_activity" not in st.session_state:
    st.session_state.last_activity = time.time()

# 🔐 LOGIN
def login():
    st.markdown("<h1>🔐 Login System</h1>", unsafe_allow_html=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if password:
        score, label, color = password_strength(password)
        st.markdown(
            f"""<div style="background:#2c2f3a; border-radius:6px; height:8px; margin-bottom:4px;">
            <div style="background:{color}; width:{score*20}%; height:8px; border-radius:6px;"></div>
            </div>""",
            unsafe_allow_html=True
        )
        st.caption(f"Password strength: {label}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            if not email:
                st.warning("Please enter your email.")
            else:
                locked, remaining_min = is_locked_out(email)
                if locked:
                    st.error(f"🔒 Account temporarily locked due to repeated failed attempts. Try again in {remaining_min} minute(s).")
                else:
                    try:
                        with st.spinner("Signing in..."):
                            user = auth.sign_in_with_email_and_password(email, password)
                            time.sleep(0.3)

                        reset_login_attempts(email)
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.id_token = user["idToken"]
                        st.session_state.last_activity = time.time()
                        log_audit("login_success")

                        st.success("Login successful")
                        st.rerun()

                    except Exception as e:
                        record_failed_attempt(email)
                        log_audit("login_failed", str(e))
                        st.error(f"Login failed: {e}")

    with col2:
        if st.button("Register"):
            try:
                with st.spinner("Creating account..."):
                    auth.create_user_with_email_and_password(email, password)
                    time.sleep(0.3)
                log_audit("account_registered", email)
                st.success("Account created successfully")

            except Exception as e:
                st.error(f"Register failed: {e}")

    with st.expander("Forgot password?"):
        reset_email = st.text_input("Enter your account email", key="reset_email")
        if st.button("Send password reset email"):
            if reset_email:
                try:
                    auth.send_password_reset_email(reset_email)
                    log_audit("password_reset_requested", reset_email)
                    st.success("If this email is registered, a password reset link has been sent.")
                except Exception as e:
                    st.error(f"Could not send reset email: {e}")
            else:
                st.warning("Please enter your email first.")

if not st.session_state.logged_in:
    login()
    st.stop()

check_session_timeout()

# 🔓 LOGOUT
st.sidebar.markdown(f"### 👤 {st.session_state.user_email}")

cleanup_on_logout = st.sidebar.checkbox("🧹 Delete my posts on logout (testing mode)")

if st.sidebar.button("Logout"):
    if cleanup_on_logout:
        with st.spinner("Cleaning up your test posts..."):
            all_posts = db.child("posts").get(get_token())
            if all_posts.each():
                for post in all_posts.each():
                    if post.val().get("user") == st.session_state.user_email:
                        db.child("posts").child(post.key()).remove(get_token())
        log_audit("logout_with_cleanup")
    else:
        log_audit("logout")

    st.session_state.logged_in = False
    st.rerun()

# 📦 MODEL LOAD
model = pickle.load(
    open(os.path.join(BASE_DIR, "cyberbullying_model.pkl"), "rb")
)

vectorizer = pickle.load(
    open(os.path.join(BASE_DIR, "tfidf_vectorizer.pkl"), "rb")
)

# 🤖 PREDICTION
def predict(text):
    vec = vectorizer.transform([clean_text(text)])
    pred = model.predict(vec)[0]
    prob = model.predict_proba(vec)[0][1]
    return pred, prob

# 🔴 TOXIC WORD DETECTION
def get_toxic_words(text, top_n=5):
    try:
        cleaned = clean_text(text)
        words = cleaned.split()
        feature_names = vectorizer.get_feature_names_out()
        coefs = model.coef_[0]
        word_coef = dict(zip(feature_names, coefs))

        scored = []
        seen = set()
        for w in words:
            if w in word_coef and w not in seen:
                scored.append((w, word_coef[w]))
                seen.add(w)

        scored.sort(key=lambda x: x[1], reverse=True)
        toxic_words = [w for w, c in scored if c > 0][:top_n]
        return toxic_words
    except Exception:
        return []

# 😊 SENTIMENT ANALYSIS
def get_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        return "Positive", polarity
    elif polarity < -0.1:
        return "Negative", polarity
    else:
        return "Neutral", polarity

def sentiment_badge(label):
    cls = {"Positive": "badge-sentiment-pos", "Negative": "badge-sentiment-neg", "Neutral": "badge-sentiment-neu"}[label]
    emoji = {"Positive": "😊", "Negative": "😔", "Neutral": "😐"}[label]
    return f'<span class="{cls}">{emoji} {label}</span>'

# 💬 AI REPLY / REPHRASING SUGGESTIONS
REPHRASE_MAP = {
    "hate": "dislike", "stupid": "confusing to me", "idiot": "person I disagree with",
    "ugly": "not to my taste", "dumb": "hard to understand", "loser": "person having a tough time",
    "worthless": "struggling right now", "shut up": "please let me finish", "kill": "stop",
    "die": "go away", "fat": "different body type", "trash": "not great", "garbage": "not great",
    "pathetic": "disappointing", "freak": "unusual person", "dirty": "unpleasant",
}

CALM_RESPONSE_TEMPLATES = [
    "I don't think that's a fair thing to say. Let's keep this respectful.",
    "That comment hurt, and I'd like us to talk this out calmly instead.",
    "I'm going to step away from this conversation for now. We can revisit it later.",
    "I understand you might be upset, but this kind of language isn't okay.",
    "I'm not going to respond to that, but I am reporting/blocking it so it doesn't continue.",
]

def suggest_rephrase(text):
    """Return a gently reworded version of text using a simple substitution
    dictionary. This is a rule-based suggestion tool, not a generative model."""
    result = text
    replaced_any = False
    for toxic_word, gentle_word in REPHRASE_MAP.items():
        pattern = re.compile(rf'\b({re.escape(toxic_word)})\b', re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(gentle_word, result)
            replaced_any = True
    return result, replaced_any

def get_calm_response(seed_text):
    idx = abs(hash(seed_text)) % len(CALM_RESPONSE_TEMPLATES)
    return CALM_RESPONSE_TEMPLATES[idx]

# 📄 PDF REPORT GENERATOR
def generate_pdf_report(total, bully, safe, user_toxic):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Cyberbullying Detector - Summary Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 8, f"Total posts analyzed: {total}", ln=True)
    pdf.cell(0, 8, f"Cyberbullying posts: {bully}", ln=True)
    pdf.cell(0, 8, f"Safe posts: {safe}", ln=True)
    pct = round((bully / total) * 100, 1) if total > 0 else 0
    pdf.cell(0, 8, f"Cyberbullying rate: {pct}%", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Flagged users (2+ toxic posts):", ln=True)
    pdf.set_font("Helvetica", "", 11)
    flagged_any = False
    for u, c in user_toxic.items():
        if c >= 2:
            pdf.cell(0, 8, f"- {u}: {c} toxic posts", ln=True)
            flagged_any = True
    if not flagged_any:
        pdf.cell(0, 8, "None", ln=True)
    return bytes(pdf.output())

# 🎯 HEADER
st.markdown("<h1>🚫 Cyberbullying Detector PRO</h1>", unsafe_allow_html=True)

# 📥 FETCH ALL POSTS ONCE (shared across tabs)
with st.spinner("Loading data..."):
    posts = db.child("posts").get(get_token())

total = 0
bully = 0
safe = 0
data_list = []
user_toxic = {}
posts_records = []

if posts.each():
    for post in reversed(posts.each()):
        d = post.val()
        post_id = post.key()
        user = d.get("user", "Unknown")
        d["text"] = decrypt_text(d.get("text", ""))

        if user not in user_toxic:
            user_toxic[user] = 0
        if d.get("result") == 1:
            user_toxic[user] += 1

        total += 1
        if d.get("result") == 1:
            bully += 1
        else:
            safe += 1

        posts_records.append({"id": post_id, "data": d, "user": user})

        data_list.append({
            "User": user,
            "Text": d.get("text", ""),
            "Platform": d.get("platform", "Unknown"),
            "Result": "Cyberbullying" if d.get("result") == 1 else "Safe",
            "Time": d.get("time", "")
        })

# ⚠️ AUTO-WARNING BANNER
my_toxic_count = user_toxic.get(st.session_state.user_email, 0)
if my_toxic_count >= 2:
    st.warning(f"⚠️ Notice: your account has {my_toxic_count} posts flagged as cyberbullying. Repeated violations may affect your standing on this platform.")

# 📑 TABS
tab_analyze, tab_history, tab_dashboard, tab_youtube, tab_voice, tab_quiz = st.tabs(
    ["🔍 Analyze", "📜 History", "📊 Dashboard", "📺 YouTube Check", "🎙️ Voice Check", "🎯 Awareness Quiz"]
)

# ================= ANALYZE TAB =================
with tab_analyze:

    text = st.text_area(
        "Enter Text",
        placeholder="Example: I hate you"
    )

    platform = st.selectbox(
        "Platform",
        ["Facebook", "Instagram", "Twitter", "YouTube"]
    )

    if st.button("Analyze"):

        if not text:
            st.warning("Please enter some text first.")
        elif not check_rate_limit():
            st.error(f"⏱️ Rate limit exceeded: max {RATE_LIMIT_COUNT} analyses per {RATE_LIMIT_WINDOW} seconds. Please wait a moment and try again.")
        else:

            with st.spinner("Analyzing text..."):
                result, prob = predict(text)
                toxic_words = get_toxic_words(text)
                sentiment_label, polarity = get_sentiment(text)
                time.sleep(0.4)

            st.progress(int(prob * 100))
            st.write(f"Confidence: {round(prob*100,2)}%")

            if result == 1:
                if prob > 0.8:
                    st.error(f"🚨 HIGH Cyberbullying ({prob*100:.2f}%)")
                elif prob > 0.5:
                    st.warning(f"⚠️ Medium Risk ({prob*100:.2f}%)")
                else:
                    st.info(f"😐 Low Risk ({prob*100:.2f}%)")
            else:
                st.success(f"😊 Safe ({prob*100:.2f}%)")

            st.markdown(sentiment_badge(sentiment_label), unsafe_allow_html=True)
            st.caption(f"Sentiment polarity score: {round(polarity, 3)}")

            if toxic_words:
                st.write("")
                st.markdown("**Flagged words in your text:**")
                st.markdown(highlight_text(text, toxic_words), unsafe_allow_html=True)
                st.caption("Highlighted words contributed most strongly to the cyberbullying classification.")

            bangla_hits = check_bangla_toxic(text)
            if bangla_hits:
                st.info(f"🇧🇩 Bangla/Banglish keyword check flagged: {', '.join(bangla_hits)} (supplementary check, not part of the ML model's decision).")

            if result == 1:
                st.write("")
                st.markdown("### 💬 Suggested Actions")

                rephrased, changed = suggest_rephrase(text)
                tab_sug1, tab_sug2 = st.tabs(["✍️ Rephrase this message", "🧘 If you received this"])

                with tab_sug1:
                    if changed:
                        st.caption("A gentler way to express a similar point:")
                        st.info(rephrased)
                    else:
                        st.caption("Consider rephrasing without harsh or personal language.")

                with tab_sug2:
                    st.caption("If someone sent you a message like this, here's a calm way to respond:")
                    st.info(get_calm_response(text))
                    st.caption("You can also use the Report / Block options in the History tab for messages from other users.")

            db.child("posts").push({
                "text": encrypt_text(text),
                "platform": platform,
                "result": int(result),
                "confidence": float(prob),
                "sentiment": sentiment_label,
                "user": st.session_state.user_email,
                "time": str(datetime.datetime.now()),
                "reactions": {
                    "like": 0,
                    "love": 0,
                    "haha": 0,
                    "angry": 0
                }
            }, get_token())

# ================= HISTORY TAB =================
with tab_history:

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        search_query = st.text_input("Search text", placeholder="Search by keyword...")

    with col_s2:
        platform_filter = st.selectbox("Filter by platform", ["All", "Facebook", "Instagram", "Twitter", "YouTube"])

    user_filter = st.text_input("Filter by user email", placeholder="e.g. name@gmail.com")

    st.write("---")

    blocked_list = get_blocked_users()

    filtered_records = posts_records

    if search_query:
        filtered_records = [r for r in filtered_records if search_query.lower() in r["data"].get("text", "").lower()]

    if platform_filter != "All":
        filtered_records = [r for r in filtered_records if r["data"].get("platform") == platform_filter]

    if user_filter:
        filtered_records = [r for r in filtered_records if user_filter.lower() in r["user"].lower()]

    filtered_records = [r for r in filtered_records if not is_blocked(r["user"], blocked_list)]

    if blocked_list:
        with st.expander(f"🚫 Blocked users ({len(blocked_list)})"):
            for b in blocked_list:
                display_name = b.replace("_at_", "@").replace("_", ".")
                col_b1, col_b2 = st.columns([3, 1])
                with col_b1:
                    st.write(display_name)
                with col_b2:
                    if st.button("Unblock", key="unblock_"+b):
                        unblock_user(display_name)
                        st.rerun()

    if not filtered_records:
        st.info("No posts match your search/filter criteria.")

    for record in filtered_records:

        d = record["data"]
        post_id = record["id"]
        user = record["user"]

        badge_class = "badge-bully" if d.get("result") == 1 else "badge-safe"
        badge_text = f"😡 Cyberbullying ({round(d.get('confidence', 0)*100,2)}%)" if d.get("result") == 1 else f"😊 Safe ({round(d.get('confidence', 0)*100,2)}%)"
        sentiment_label = d.get("sentiment")
        sentiment_html = sentiment_badge(sentiment_label) if sentiment_label else ""

        st.markdown(f"""
        <div class="post-card">
            <div class="post-header">👤 {user} &nbsp;|&nbsp; 📱 {d.get("platform", "Unknown")}</div>
            <div class="post-text">{html.escape(d.get("text", ""))}</div>
            <span class="{badge_class}">{badge_text}</span>{sentiment_html}
        </div>
        """, unsafe_allow_html=True)

        r = d.get("reactions", {})
        like = r.get("like", 0)
        love = r.get("love", 0)
        haha = r.get("haha", 0)
        angry = r.get("angry", 0)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button(f"👍 {like}", key="l"+post_id):
                r["like"] = like + 1

        with col2:
            if st.button(f"❤️ {love}", key="lo"+post_id):
                r["love"] = love + 1

        with col3:
            if st.button(f"😂 {haha}", key="h"+post_id):
                r["haha"] = haha + 1

        with col4:
            if st.button(f"😡 {angry}", key="a"+post_id):
                r["angry"] = angry + 1

        db.child("posts").child(post_id).update({
            "reactions": r
        }, get_token())

        score = like + love + haha - angry
        st.caption(f"🔥 Score: {score}")

        if score < 0:
            st.error("🚨 Negative Post")

        comment = st.text_input("Comment", key="c"+post_id)

        if st.button("Post", key="b"+post_id):
            if comment:
                db.child("posts").child(post_id).child("comments").push({
                    "user": st.session_state.user_email,
                    "text": comment
                }, get_token())
                st.rerun()

        comments = d.get("comments")
        if comments:
            for cm in comments.values():
                st.write(f"💬 {cm.get('user', 'Unknown')}: {cm.get('text', '')}")

        if user == st.session_state.user_email:
            if st.button("Delete", key="d"+post_id):
                db.child("posts").child(post_id).remove(get_token())
                log_audit("post_deleted", post_id)
                st.rerun()
        else:
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("🚩 Report", key="rep"+post_id):
                    report_post(post_id, user, d.get("text", ""))
                    st.success(f"Reported {user}'s post to admins.")
            with col_r2:
                if st.button("🚫 Block user", key="blk"+post_id):
                    block_user(user)
                    st.success(f"Blocked {user}. Their posts are now hidden from your view.")
                    st.rerun()

        st.write("---")

# ================= DASHBOARD TAB =================
with tab_dashboard:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""<div class="metric-box"><div class="metric-number">{total}</div><div class="metric-label">Total posts</div></div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="metric-box"><div class="metric-number">{bully}</div><div class="metric-label">Cyberbullying</div></div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""<div class="metric-box"><div class="metric-number">{safe}</div><div class="metric-label">Safe</div></div>""", unsafe_allow_html=True)

    st.write("")

    if total > 0:
        fig = go.Figure(data=[go.Pie(
            labels=["Cyberbullying", "Safe"],
            values=[bully, safe],
            hole=0.55,
            marker=dict(colors=["#f87171", "#4ade80"]),
            textinfo="label+percent"
        )])
        fig.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f1f1f3")
        )
        st.plotly_chart(fig, use_container_width=True)

    # 📈 TIME-TREND CHART
    if total > 0:
        st.subheader("📈 Posts Over Time")
        try:
            df_time = pd.DataFrame(data_list)
            df_time["Time"] = pd.to_datetime(df_time["Time"], errors="coerce")
            df_time = df_time.dropna(subset=["Time"])
            df_time["Date"] = df_time["Time"].dt.date

            trend = df_time.groupby(["Date", "Result"]).size().unstack(fill_value=0)
            for col in ["Safe", "Cyberbullying"]:
                if col not in trend.columns:
                    trend[col] = 0

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=trend.index, y=trend["Safe"], mode="lines+markers",
                name="Safe", line=dict(color="#4ade80", width=2)
            ))
            fig_trend.add_trace(go.Scatter(
                x=trend.index, y=trend["Cyberbullying"], mode="lines+markers",
                name="Cyberbullying", line=dict(color="#f87171", width=2)
            ))
            fig_trend.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f1f1f3"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(gridcolor="#2c2f3a"),
                yaxis=dict(gridcolor="#2c2f3a"),
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        except Exception:
            st.caption("Not enough time-stamped data yet to show a trend.")

    # ☁️ WORD CLOUD OF TOXIC WORDS
    if bully > 0:
        st.subheader("☁️ Toxic Word Cloud")
        toxic_texts = " ".join([
            clean_text(r["data"].get("text", ""))
            for r in posts_records if r["data"].get("result") == 1
        ])
        if toxic_texts.strip():
            wc = WordCloud(
                width=800, height=350,
                background_color="#0e1117",
                colormap="Reds"
            ).generate(toxic_texts)
            st.image(wc.to_array(), use_container_width=True)

    st.subheader("🚨 Toxic Users")

    for u, c in user_toxic.items():
        if c >= 2:
            st.error(f"{u} → {c} toxic posts")

    if data_list:
        df = pd.DataFrame(data_list)
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "Download CSV",
                df.to_csv(index=False),
                "report.csv"
            )
        with col_dl2:
            pdf_bytes = generate_pdf_report(total, bully, safe, user_toxic)
            st.download_button(
                "Download PDF Summary",
                data=pdf_bytes,
                file_name="summary_report.pdf",
                mime="application/pdf"
            )

    ADMIN_EMAIL = st.secrets["app"]["admin_email"]

    if st.session_state.user_email == ADMIN_EMAIL:
        st.subheader("👑 Admin Moderation Panel")

        flagged_posts = [r for r in posts_records if r["data"].get("result") == 1]

        if not flagged_posts:
            st.caption("No flagged posts to review.")

        for record in flagged_posts:
            d = record["data"]
            pid = record["id"]
            reviewed = d.get("reviewed", False)
            status = "✅ Reviewed" if reviewed else "⏳ Pending review"

            st.markdown(f"**{record['user']}** — {status}")
            st.write(d.get("text", ""))

            colA, colB = st.columns(2)
            with colA:
                if st.button("Confirm violation", key="cv"+pid):
                    db.child("posts").child(pid).update({"reviewed": True}, get_token())
                    log_audit("admin_confirm_violation", pid)
                    st.rerun()
            with colB:
                if st.button("Overturn (mark safe)", key="ov"+pid):
                    db.child("posts").child(pid).update({"result": 0, "reviewed": True}, get_token())
                    log_audit("admin_overturn", pid)
                    st.rerun()
            st.write("---")

        st.write("")
        if st.button("Delete ALL Posts"):
            db.child("posts").remove(get_token())
            log_audit("admin_delete_all_posts")
            st.rerun()

        with st.expander("🚩 Reported Posts"):
            reports_data = db.child("reports").get(get_token())
            if reports_data.each():
                report_entries = [r.val() for r in reports_data.each()]

                report_counts = {}
                for r in report_entries:
                    ru = r.get("reported_user", "Unknown")
                    report_counts[ru] = report_counts.get(ru, 0) + 1

                st.markdown("**Most-reported users:**")
                for u, c in sorted(report_counts.items(), key=lambda x: x[1], reverse=True):
                    st.error(f"{u} → reported {c} time(s)")

                st.markdown("---")
                st.markdown("**All reports:**")
                for r in reversed(report_entries):
                    st.caption(
                        f"`{r.get('time','')}` — **{r.get('reported_user','')}** reported by "
                        f"**{r.get('reported_by','')}** — \"{r.get('reason','')}\""
                    )
            else:
                st.caption("No reports submitted yet.")

        with st.expander("📝 View Audit Log (last 30 events)"):
            audit_data = db.child("audit_log").get(get_token())
            if audit_data.each():
                entries = [e.val() for e in audit_data.each()]
                entries = list(reversed(entries))[:30]
                for entry in entries:
                    st.caption(
                        f"`{entry.get('time','')}` — **{entry.get('user','')}** — "
                        f"{entry.get('action','')} {('(' + entry.get('details','') + ')') if entry.get('details') else ''}"
                    )
            else:
                st.caption("No audit events recorded yet.")

# ================= YOUTUBE CHECK TAB =================
with tab_youtube:

    st.markdown("Check the comments on a YouTube video for cyberbullying using the YouTube Data API.")

    st.caption(
        "You need a free YouTube Data API v3 key from Google Cloud Console "
        "(console.cloud.google.com → APIs & Services → Credentials)."
    )

    yt_api_key = st.text_input("YouTube API Key", type="password")
    yt_url = st.text_input("YouTube video URL or ID", placeholder="https://www.youtube.com/watch?v=...")
    max_comments = st.slider("Number of comments to check", 10, 100, 30, step=10)

    if st.button("Check Video Comments"):

        if not yt_api_key or not yt_url:
            st.warning("Please provide both an API key and a video URL/ID.")
        else:
            try:
                from googleapiclient.discovery import build

                video_id = extract_youtube_video_id(yt_url)

                with st.spinner("Fetching comments from YouTube..."):
                    youtube = build("youtube", "v3", developerKey=yt_api_key)
                    request = youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=max_comments,
                        textFormat="plainText"
                    )
                    response = request.execute()

                comments = []
                for item in response.get("items", []):
                    snippet = item["snippet"]["topLevelComment"]["snippet"]
                    comments.append({
                        "author": snippet["authorDisplayName"],
                        "text": snippet["textDisplay"]
                    })

                if not comments:
                    st.info("No comments found for this video (or comments are disabled).")
                else:
                    yt_bully = 0
                    yt_safe = 0
                    flagged_comments = []

                    with st.spinner(f"Analyzing {len(comments)} comments..."):
                        for c in comments:
                            pred, prob = predict(c["text"])
                            if pred == 1:
                                yt_bully += 1
                                flagged_comments.append({**c, "confidence": prob})
                            else:
                                yt_safe += 1

                    st.success(f"Checked {len(comments)} comments: {yt_bully} flagged as cyberbullying, {yt_safe} safe.")

                    if flagged_comments:
                        st.subheader("🚨 Flagged Comments")
                        for c in sorted(flagged_comments, key=lambda x: x["confidence"], reverse=True):
                            toxic_words = get_toxic_words(c["text"])
                            st.markdown(f"""
                            <div class="post-card">
                                <div class="post-header">👤 {html.escape(c['author'])}</div>
                                <div class="post-text">{highlight_text(c['text'], toxic_words)}</div>
                                <span class="badge-bully">😡 Cyberbullying ({round(c['confidence']*100,2)}%)</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No comments were flagged as cyberbullying on this video. 🎉")

            except ImportError:
                st.error("The google-api-python-client library is not installed. Run: pip install google-api-python-client")
            except Exception as e:
                st.error(f"Could not fetch comments: {e}")

# ================= VOICE CHECK TAB =================
with tab_voice:

    st.markdown("Upload a short voice recording to check its spoken content for cyberbullying.")
    st.caption("Supported formats: WAV, AIFF, FLAC. (MP3 requires an extra converter -- convert to WAV first if needed.)")

    audio_file = st.file_uploader("Upload audio file", type=["wav", "aiff", "flac"])

    if audio_file is not None:
        st.audio(audio_file)

        if st.button("Transcribe and Analyze"):
            try:
                import speech_recognition as sr

                with st.spinner("Transcribing audio..."):
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(audio_file) as source:
                        audio_data = recognizer.record(source)
                    transcribed_text = recognizer.recognize_google(audio_data)

                st.markdown("**Transcribed text:**")
                st.write(transcribed_text)

                with st.spinner("Analyzing transcribed text..."):
                    result, prob = predict(transcribed_text)
                    toxic_words = get_toxic_words(transcribed_text)
                    sentiment_label, polarity = get_sentiment(transcribed_text)

                st.progress(int(prob * 100))
                st.write(f"Confidence: {round(prob*100,2)}%")

                if result == 1:
                    st.error(f"🚨 Cyberbullying detected in audio ({prob*100:.2f}%)")
                else:
                    st.success(f"😊 Safe ({prob*100:.2f}%)")

                st.markdown(sentiment_badge(sentiment_label), unsafe_allow_html=True)

                if toxic_words:
                    st.markdown("**Flagged words:**")
                    st.markdown(highlight_text(transcribed_text, toxic_words), unsafe_allow_html=True)

            except ImportError:
                st.error("The SpeechRecognition library is not installed. Run: pip install SpeechRecognition")
            except sr.UnknownValueError:
                st.warning("Could not understand the audio clearly. Try a clearer recording.")
            except Exception as e:
                st.error(f"Error processing audio: {e}")

# ================= AWARENESS QUIZ TAB =================
with tab_quiz:

    st.markdown("### 🎯 Cyberbullying Awareness Quiz")
    st.caption("Test your knowledge about cyberbullying and digital citizenship.")

    QUIZ_QUESTIONS = [
        {
            "q": "Which of the following is considered a form of cyberbullying?",
            "options": ["Sending a birthday message", "Repeatedly sending threatening messages", "Sharing a public news article", "Liking a friend's post"],
            "answer": 1,
            "explanation": "Repeated threatening or harassing messages are a classic form of cyberbullying."
        },
        {
            "q": "What should you do first if you receive a threatening message online?",
            "options": ["Reply with an angrier message", "Save/screenshot the evidence and report it", "Ignore it and delete your account", "Share it publicly to embarrass the sender"],
            "answer": 1,
            "explanation": "Keeping evidence (screenshots) is important before reporting to a platform or trusted adult."
        },
        {
            "q": "Is it cyberbullying if the harmful content is anonymous?",
            "options": ["No, anonymous content doesn't count", "Yes, anonymity does not change whether the content is harmful", "Only if it's from a verified account", "Only if more than 10 people see it"],
            "answer": 1,
            "explanation": "Anonymity does not remove the harmful impact of bullying content."
        },
        {
            "q": "What is 'doxxing'?",
            "options": ["Sending funny memes", "Publishing someone's private information without consent", "Following someone on social media", "Commenting on a public post"],
            "answer": 1,
            "explanation": "Doxxing means publicly revealing private/identifying information about someone without their consent, often to harass them."
        },
        {
            "q": "Which of these is a healthy way to respond to online conflict?",
            "options": ["Escalating with insults", "Blocking/reporting and stepping away calmly", "Recruiting friends to gang up on the person", "Posting about it publicly to get sympathy"],
            "answer": 1,
            "explanation": "Disengaging calmly and using platform tools (block/report) is the safest response."
        },
    ]

    if "quiz_index" not in st.session_state:
        st.session_state.quiz_index = 0
    if "quiz_score" not in st.session_state:
        st.session_state.quiz_score = 0
    if "quiz_answered" not in st.session_state:
        st.session_state.quiz_answered = False

    idx = st.session_state.quiz_index

    if idx < len(QUIZ_QUESTIONS):
        question = QUIZ_QUESTIONS[idx]
        st.progress(idx / len(QUIZ_QUESTIONS))
        st.markdown(f"**Question {idx + 1} of {len(QUIZ_QUESTIONS)}:** {question['q']}")

        choice = st.radio("Choose one:", question["options"], key=f"quiz_choice_{idx}", index=None)

        if st.button("Submit Answer", key=f"quiz_submit_{idx}"):
            if choice is None:
                st.warning("Please select an answer.")
            else:
                selected_index = question["options"].index(choice)
                if selected_index == question["answer"]:
                    st.success("✅ Correct! " + question["explanation"])
                    st.session_state.quiz_score += 1
                else:
                    st.error("❌ Not quite. " + question["explanation"])
                st.session_state.quiz_answered = True

        if st.session_state.quiz_answered:
            if st.button("Next Question", key=f"quiz_next_{idx}"):
                st.session_state.quiz_index += 1
                st.session_state.quiz_answered = False
                st.rerun()
    else:
        st.markdown("### 🏁 Quiz Complete!")
        score = st.session_state.quiz_score
        total_q = len(QUIZ_QUESTIONS)
        st.markdown(f"**Your score: {score} / {total_q}**")

        if score == total_q:
            st.success("🌟 Excellent! You have a strong understanding of cyberbullying awareness.")
        elif score >= total_q / 2:
            st.info("👍 Good job! Review the explanations above to strengthen your understanding.")
        else:
            st.warning("📘 Consider learning more about digital citizenship and online safety.")

        if st.button("Retake Quiz"):
            st.session_state.quiz_index = 0
            st.session_state.quiz_score = 0
            st.session_state.quiz_answered = False
            st.rerun()