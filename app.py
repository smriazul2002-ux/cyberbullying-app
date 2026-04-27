import streamlit as st
import pickle
import re
import string
import os
import pyrebase

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

# 🔥 FIREBASE CONFIG (FIXED)
firebase_config = {
    "apiKey": "AIzaSyC76HgUI821jKRc8hjpPt6RxwxyK88nOrE",
    "authDomain": "cyberbullyingapp-d427c.firebaseapp.com",
    "databaseURL": "https://cyberbullyingapp-d427c-default-rtdb.firebaseio.com",
    "projectId": "cyberbullyingapp-d427c",
    "storageBucket": "cyberbullyingapp-d427c.appspot.com",  # ✅ FIXED
    "messagingSenderId": "742009273595",
    "appId": "1:742009273595:web:6ce11531f599fa2b3fc45e"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# 🔐 SESSION
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 🔐 LOGIN FUNCTION
def login():
    st.title("🔐 Firebase Login")

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
                st.success("✅ Account Created! Now login")
            except:
                st.error("❌ Registration Failed")

# 🔓 IF NOT LOGGED IN
if not st.session_state.logged_in:
    login()
    st.stop()

# 🔓 LOGOUT
st.sidebar.write("👤", st.session_state.user_email)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# 📦 LOAD MODEL
BASE_DIR = os.path.dirname(__file__)

model = pickle.load(open(os.path.join(BASE_DIR, "cyberbullying_model.pkl"), "rb"))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, "tfidf_vectorizer.pkl"), "rb"))

# 🧹 CLEAN TEXT
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

# 🤖 PREDICT
def predict(text):
    vec = vectorizer.transform([clean_text(text)])
    result = model.predict(vec)[0]
    prob = model.predict_proba(vec)[0][1]
    return result, prob

# 🎨 UI
st.title("🚫 Cyberbullying Detector")

text = st.text_area("Enter a sentence")

if st.button("Analyze"):
    if text:
        result, prob = predict(text)

        st.progress(int(prob * 100))
        st.write(f"Confidence: {round(prob*100,2)}%")

        if result == 1:
            st.error("😡 Cyberbullying Detected")
        else:
            st.success("😊 Safe Text")
    else:
        st.warning("⚠️ Please enter text")
