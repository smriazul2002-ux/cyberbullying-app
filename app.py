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

# 🔥 FIREBASE CONFIG
firebase_config = {
    "apiKey": "AIzaSyC76HgUI821jKRc8hjpPt6RxwxyK88nOrE",
    "authDomain": "cyberbullyingapp-d427c.firebaseapp.com",
    "databaseURL": "https://cyberbullyingapp-d427c-default-rtdb.firebaseio.com",
    "projectId": "cyberbullyingapp-d427c",
    "storageBucket": "cyberbullyingapp-d427c.appspot.com",
    "messagingSenderId": "742009273595",
    "appId": "1:742009273595:web:6ce11531f599fa2b3fc45e"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

# 🇧🇩 BASIC BANGLA / BANGLISH KEYWORD LEXICON (supplementary, not a full model)
# NOTE: This is a small starter list. For production or thesis-grade accuracy,
# expand this using a published Bangla abusive-language dataset.
BANGLA_TOXIC_WORDS = [
    "baje", "faltu", "boka", "pagol", "chagol", "gadha", "murkho",
    "beyadob", "shoytan", "boka chele", "boka meye"
]

def check_bangla_toxic(text):
    text_lower = str(text).lower()
    found = [w for w in BANGLA_TOXIC_WORDS if w in text_lower]
    return found

# 🔑 PASSWORD STRENGTH METER
def password_strength(password):
    if not password:
        return 0, ""
    score = 0
    if len(password) >= 8:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    labels = {0: "Very weak", 1: "Weak", 2: "Fair", 3: "Good", 4: "Strong", 5: "Very strong"}
    colors = {0: "#f87171", 1: "#f87171", 2: "#facc15", 3: "#facc15", 4: "#4ade80", 5: "#4ade80"}
    return score, labels[score], colors[score]

# 🔐 SESSION
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
            try:
                with st.spinner("Signing in..."):
                    user = auth.sign_in_with_email_and_password(email, password)
                    time.sleep(0.3)

                st.session_state.logged_in = True
                st.session_state.user_email = email

                st.success("Login successful")
                st.rerun()

            except Exception as e:
                st.error(f"Login failed: {e}")

    with col2:
        if st.button("Register"):
            try:
                with st.spinner("Creating account..."):
                    auth.create_user_with_email_and_password(email, password)
                    time.sleep(0.3)
                st.success("Account created successfully")

            except Exception as e:
                st.error(f"Register failed: {e}")

if not st.session_state.logged_in:
    login()
    st.stop()

# 🔓 LOGOUT
st.sidebar.markdown(f"### 👤 {st.session_state.user_email}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# 📦 MODEL LOAD
BASE_DIR = os.path.dirname(__file__)

model = pickle.load(
    open(os.path.join(BASE_DIR, "cyberbullying_model.pkl"), "rb")
)

vectorizer = pickle.load(
    open(os.path.join(BASE_DIR, "tfidf_vectorizer.pkl"), "rb")
)

# 🧹 CLEAN TEXT
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

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

def highlight_text(original_text, toxic_words):
    escaped = html.escape(original_text)
    for w in toxic_words:
        pattern = re.compile(rf'\b({re.escape(w)})\b', re.IGNORECASE)
        escaped = pattern.sub(r"<mark>\1</mark>", escaped)
    return escaped

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
    posts = db.child("posts").get()

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
tab_analyze, tab_history, tab_dashboard = st.tabs(["🔍 Analyze", "📜 History", "📊 Dashboard"])

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

        if text:

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

            db.child("posts").push({
                "text": text,
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
            })
        else:
            st.warning("Please enter some text first.")

# ================= HISTORY TAB =================
with tab_history:

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        search_query = st.text_input("Search text", placeholder="Search by keyword...")

    with col_s2:
        platform_filter = st.selectbox("Filter by platform", ["All", "Facebook", "Instagram", "Twitter", "YouTube"])

    user_filter = st.text_input("Filter by user email", placeholder="e.g. name@gmail.com")

    st.write("---")

    filtered_records = posts_records

    if search_query:
        filtered_records = [r for r in filtered_records if search_query.lower() in r["data"].get("text", "").lower()]

    if platform_filter != "All":
        filtered_records = [r for r in filtered_records if r["data"].get("platform") == platform_filter]

    if user_filter:
        filtered_records = [r for r in filtered_records if user_filter.lower() in r["user"].lower()]

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
        })

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
                })
                st.rerun()

        comments = d.get("comments")
        if comments:
            for cm in comments.values():
                st.write(f"💬 {cm.get('user', 'Unknown')}: {cm.get('text', '')}")

        if user == st.session_state.user_email:
            if st.button("Delete", key="d"+post_id):
                db.child("posts").child(post_id).remove()
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

    ADMIN_EMAIL = "your@email.com"

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
                    db.child("posts").child(pid).update({"reviewed": True})
                    st.rerun()
            with colB:
                if st.button("Overturn (mark safe)", key="ov"+pid):
                    db.child("posts").child(pid).update({"result": 0, "reviewed": True})
                    st.rerun()
            st.write("---")

        st.write("")
        if st.button("Delete ALL Posts"):
            db.child("posts").remove()
            st.rerun()