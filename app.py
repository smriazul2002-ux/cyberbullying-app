import streamlit as st
import pickle
import re
import string
import os
import pyrebase
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# 🔥 PAGE CONFIG
st.set_page_config(page_title="Cyberbullying Detector", layout="centered")

# 🎨 STYLE
st.markdown("""
<style>
.stButton>button {
    width: 100%;
    border-radius: 10px;
    height: 3em;
}
</style>
""", unsafe_allow_html=True)

# 🔥 Firebase config
firebase_config = {
    "apiKey": "AIzaSyC76HgUI821jKRc8hjpPt6RxwxyK88nOrE",
    "authDomain": "cyberbullyingapp-d427c.firebaseapp.com",
    "databaseURL": "https://cyberbullyingapp-d427c-default-rtdb.firebaseio.com",
    "projectId": "cyberbullyingapp-d427c",
    "storageBucket": "cyberbullyingapp-d427c.firebasestorage.app",
    "messagingSenderId": "742009273595",
    "appId": "1:742009273595:web:6ce11531f599fa2b3fc45e"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

# 🔐 LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 Firebase Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            auth.sign_in_with_email_and_password(email, password)
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.rerun()
        except:
            st.error("❌ Login Failed")

if not st.session_state.logged_in:
    login()
    st.stop()

# 🔓 LOGOUT
if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.write("👤 Logged in as:", st.session_state.user_email)

ADMIN_EMAIL = "your@email.com"

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

# 🎨 UI
st.title("🚫😡 AI Cyberbullying Detector 🔥")

text = st.text_area("Enter text")

platform = st.selectbox("Platform", ["Facebook","YouTube","Twitter","Instagram"])

filter_platform = st.selectbox("Filter Platform", ["All","Facebook","YouTube","Twitter","Instagram"])
filter_result = st.selectbox("Filter Result", ["All","Cyberbullying","Safe"])

# 🔍 CHECK
if st.button("Check"):
    if text:
        result, prob = predict(text)

        st.progress(int(prob*100))
        st.write(f"Confidence: {round(prob*100,2)}%")

        if result == 1:
            st.error("😡 Cyberbullying")
        else:
            st.success("😊 Safe")

        data = {
            "text": text,
            "platform": platform,
            "result": int(result),
            "confidence": float(prob),
            "user": st.session_state.user_email,
            "time": str(datetime.datetime.now()),
            "reactions": {"like":0,"love":0,"haha":0,"angry":0},
            "hidden": False
        }

        db.child("posts").push(data)

# 📜 HISTORY
st.subheader("📜 History")

posts = db.child("posts").get()

total = bully = safe = 0
data_list = []
user_stats = {}

if posts.each():
    for post in reversed(posts.each()):
        d = post.val()
        post_id = post.key()

        text_val = d.get("text", "")
        platform_val = d.get("platform", "Unknown")
        result_val = d.get("result", 0)
        confidence_val = d.get("confidence", 0)
        user_val = d.get("user", "Unknown")
        time_val = d.get("time", "Old Data")

        total += 1
        if result_val == 1:
            bully += 1
        else:
            safe += 1

        user_stats[user_val] = user_stats.get(user_val, 0) + (1 if result_val == 1 else 0)

        if filter_platform!="All" and platform_val!=filter_platform:
            continue
        if filter_result=="Cyberbullying" and result_val!=1:
            continue
        if filter_result=="Safe" and result_val!=0:
            continue

        r = d.get("reactions", {})
        like = r.get("like",0)
        love = r.get("love",0)
        haha = r.get("haha",0)
        angry = r.get("angry",0)

        if angry >= 5:
            db.child("posts").child(post_id).update({"hidden":True})

        if d.get("hidden"):
            st.warning("🚫 Hidden due to negative reactions")
            continue

        st.write("👤", user_val)
        st.write("📝", text_val)
        st.write("📱", platform_val)
        st.write("⏱", time_val)

        if result_val == 1:
            st.error("Cyberbullying")
        else:
            st.success("Safe")

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

        score = like + love + haha - angry
        st.write("🔥 Score:", score)

        if score < 0:
            st.error("🚨 Highly Negative")

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
                st.write(f"💬 {cm.get('user','User')}: {cm.get('text','')}")

        if user_val == st.session_state.user_email:
            if st.button("Delete", key="d"+post_id):
                db.child("posts").child(post_id).remove()
                st.rerun()

        st.write("---")

        data_list.append({
            "User": user_val,
            "Text": text_val,
            "Platform": platform_val,
            "Result": "Cyberbullying" if result_val==1 else "Safe",
            "Confidence": round(confidence_val*100,2)
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

# 📊 REACTION ANALYTICS
total_like=total_love=total_haha=total_angry=0

if posts.each():
    for post in posts.each():
        r = post.val().get("reactions",{})
        total_like+=r.get("like",0)
        total_love+=r.get("love",0)
        total_haha+=r.get("haha",0)
        total_angry+=r.get("angry",0)

st.subheader("📊 Reaction Analytics")

fig,ax = plt.subplots()
ax.bar(["Like","Love","Haha","Angry"], [total_like,total_love,total_haha,total_angry])
st.pyplot(fig)

# 🏆 TOXIC USERS
st.subheader("🏆 Toxic Users")
for u,c in user_stats.items():
    if c>2:
        st.error(f"{u} → {c} toxic posts")

# 📥 DOWNLOAD
if data_list:
    df = pd.DataFrame(data_list)
    st.download_button("📥 Download CSV", df.to_csv(index=False), "report.csv")

# 👑 ADMIN
if st.session_state.user_email == ADMIN_EMAIL:
    st.subheader("👑 Admin Panel")
    if st.button("⚠️ Delete ALL Posts"):
        db.child("posts").remove()
        st.rerun()