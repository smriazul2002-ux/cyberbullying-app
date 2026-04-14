import streamlit as st
import pickle
import re
import string
import os
import matplotlib.pyplot as plt

# 🔐 LOGIN SYSTEM
USER_CREDENTIALS = {
    "admin": "1234",
    "user": "pass"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 Login Page")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.success("✅ Login Successful")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

def logout():
    st.session_state.logged_in = False

# 📝 History setup
if "history" not in st.session_state:
    st.session_state.history = []

# যদি login না করা থাকে → login page দেখাও
if not st.session_state.logged_in:
    login()
    st.stop()

# 📦 Load model
BASE_DIR = os.path.dirname(__file__)

model = pickle.load(open(os.path.join(BASE_DIR, "cyberbullying_model.pkl"), "rb"))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, "tfidf_vectorizer.pkl"), "rb"))

# 🧹 Clean text
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

# 🤖 Prediction
def predict(text):
    text = clean_text(text)
    text_tfidf = vectorizer.transform([text])
    pred = model.predict(text_tfidf)[0]
    prob = model.predict_proba(text_tfidf)[0][1]
    return pred, prob

# 🎨 UI
st.title("🚫😡 AI Cyberbullying Detector 🔥")

# 🔓 Logout
if st.button("Logout"):
    logout()
    st.rerun()

text = st.text_area("Enter text", placeholder="Example: I hate you / tui kharap")

# 🔍 Analyze
if st.button("Check"):
    if not text:
        st.warning("⚠️ Please enter text")
    else:
        result, prob = predict(text)

        if result == 1:
            st.error(f"😡 Cyberbullying ({round(prob*100,2)}%)")
        else:
            st.success(f"😊 Not Cyberbullying ({round(prob*100,2)}%)")

        st.progress(int(prob * 100))
        st.write(f"Confidence: {round(prob*100,2)}%")

        st.session_state.history.append((text, result, prob))

# 📜 History
st.subheader("📝 History")

for t, r, p in st.session_state.history:
    label = "😡 Cyberbullying" if r == 1 else "😊 Not Cyberbullying"
    st.write(f"{t} → {label} ({round(p*100,2)}%)")

# 📊 Analytics
st.subheader("📊 Analytics")

total = len(st.session_state.history)
bully = sum(1 for x in st.session_state.history if x[1] == 1)
safe = total - bully

st.write(f"Total Checked: {total}")
st.write(f"Cyberbullying Detected: {bully}")

# 📊 Pie Chart
if total > 0:
    labels = ['Cyberbullying', 'Not Cyberbullying']
    values = [bully, safe]

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    st.pyplot(fig)

# 📥 Download report
st.subheader("📥 Download Report")

report = ""
for t, r, p in st.session_state.history:
    label = "Cyberbullying" if r == 1 else "Not Cyberbullying"
    report += f"{t} → {label} ({round(p*100,2)}%)\n"

st.download_button(
    label="Download History",
    data=report,
    file_name="report.txt"
)