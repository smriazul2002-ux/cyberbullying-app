import streamlit as st
st.set_page_config(page_title="Cyberbullying Pro", layout="centered")

import pickle
import re
import string
import os
import pyrebase
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# 🎨 STYLE
st.markdown("""
<style>
.main { background-color: #0e1117; }
h1 { text-align: center; }
.block-container { padding-top: 2rem; }
.stTextArea textarea { border-radius: 10px; }
.stButton>button { width:100%; border-radius:10px; height:3em; }
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

# 🔐 SESSION
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 🔐 LOGIN
def login():
    st.title("🔐 Login System")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            try:
                auth.sign_in_with_email_and_password(email, password)
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.rerun()
            except:
                st.error("❌ Login Failed")

    with col2:
        if st.button("Register"):
            try:
                auth.create_user_with_email_and_password(email, password)
                st.success("✅ Account created")
            except:
                st.error("❌ Register Failed")

if not st.session_state.logged_in:
    login()
    st.stop()

# 🔓 LOGOUT
st.sidebar.write("👤", st.session_state.user_email)
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# 📦 MODEL
BASE_DIR = os.path.dirname(__file__)
model = pickle.load(open(os.path.join(BASE_DIR, "cyberbullying_model.pkl"), "rb"))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, "tfidf_vectorizer.pkl"), "rb"))

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

def predict(text):
    vec = vectorizer.transform([clean_text(text)])
    return model.predict(vec)[0], model.predict_proba(vec)[0][1]

# 🎯 UI
st.title("🚫 Cyberbullying Detector PRO")

text = st.text_area("Enter text")
platform = st.selectbox("Platform", ["Facebook","YouTube","Twitter","Instagram"])

# 🔍 ANALYZE
if st.button("Analyze"):
    if text:
        result, prob = predict(text)

        st.progress(int(prob*100))
        st.write(f"Confidence: {round(prob*100,2)}%")

        if result == 1:
            if prob > 0.8:
                st.error(f"🚨 HIGH Cyberbullying ({prob*100:.2f}%)")
            elif prob > 0.5:
                st.warning(f"⚠️ Medium Risk ({prob*100:.2f}%)")
            else:
                st.info(f"Low Risk ({prob*100:.2f}%)")
        else:
            st.success(f"😊 Safe ({prob*100:.2f}%)")

        db.child("posts").push({
            "text": text,
            "platform": platform,
            "result": int(result),
            "confidence": float(prob),
            "user": st.session_state.user_email,
            "time": str(datetime.datetime.now()),
            "reactions": {"like":0,"love":0,"haha":0,"angry":0}
        })

# 📜 HISTORY
st.subheader("📜 History")

posts = db.child("posts").get()

total = bully = safe = 0
data_list = []
user_toxic = {}

if posts.each():
    for post in reversed(posts.each()):
        d = post.val()
        post_id = post.key()

        user = d["user"]

        # Toxic count
        if user not in user_toxic:
            user_toxic[user] = 0
        if d["result"] == 1:
            user_toxic[user] += 1

        total += 1
        if d["result"] == 1:
            bully += 1
        else:
            safe += 1

        st.write("👤", user)
        st.write("📝", d["text"])
        st.write("📱", d["platform"])

        if d["result"] == 1:
            st.error(f"😡 Cyberbullying ({round(d['confidence']*100,2)}%)")
        else:
            st.success(f"😊 Safe ({round(d['confidence']*100,2)}%)")

        r = d.get("reactions", {})
        like = r.get("like",0)
        love = r.get("love",0)
        haha = r.get("haha",0)
        angry = r.get("angry",0)

        col1,col2,col3,col4 = st.columns(4)

        with col1:
            if st.button(f"👍 {like}", key="l"+post_id):
                r["like"]=like+1
        with col2:
            if st.button(f"❤️ {love}", key="lo"+post_id):
                r["love"]=love+1
        with col3:
            if st.button(f"😂 {haha}", key="h"+post_id):
                r["haha"]=haha+1
        with col4:
            if st.button(f"😡 {angry}", key="a"+post_id):
                r["angry"]=angry+1

        db.child("posts").child(post_id).update({"reactions":r})

        # 🔥 SCORE
        score = like + love + haha - angry
        st.write("🔥 Score:", score)
        if score < 0:
            st.error("🚨 Negative Post")

        # 💬 COMMENT
        comment = st.text_input("Comment", key="c"+post_id)

        if st.button("Post", key="b"+post_id):
            if comment:
                db.child("posts").child(post_id).child("comments").push({
                    "user": user,
                    "text": comment
                })
                st.rerun()

        comments = d.get("comments")
        if comments:
            for cm in comments.values():
                st.write(f"💬 {cm['user']}: {cm['text']}")

        # 🗑 DELETE
        if user == st.session_state.user_email:
            if st.button("Delete", key="d"+post_id):
                db.child("posts").child(post_id).remove()
                st.rerun()

        st.write("---")

        data_list.append({
            "User": user,
            "Text": d["text"],
            "Platform": d["platform"],
            "Result": "Cyberbullying" if d["result"]==1 else "Safe"
        })

# 📊 DASHBOARD
st.subheader("📊 Dashboard")
st.write("Total:", total)
st.write("Cyberbullying:", bully)
st.write("Safe:", safe)

if total>0:
    fig,ax = plt.subplots()
    ax.pie([bully,safe], labels=["Cyberbullying","Safe"], autopct="%1.1f%%")
    st.pyplot(fig)

# 🚨 Toxic Users
st.subheader("🚨 Toxic Users")
for u,c in user_toxic.items():
    if c >= 2:
        st.error(f"{u} → {c} toxic posts")

# 📥 DOWNLOAD
if data_list:
    df = pd.DataFrame(data_list)
    st.download_button("Download CSV", df.to_csv(index=False), "report.csv")

# 👑 ADMIN
ADMIN_EMAIL = "your@email.com"
if st.session_state.user_email == ADMIN_EMAIL:
    st.subheader("👑 Admin Panel")
    if st.button("Delete ALL Posts"):
        db.child("posts").remove()
        st.rerun()