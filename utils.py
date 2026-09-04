"""
utils.py - Pure helper functions for the Cyberbullying Detector app.
Kept separate from app.py so they can be unit-tested without needing
Streamlit, Firebase, or the ML model to be loaded.
"""

import re
import string
import html

# 🇧🇩 BASIC BANGLA / BANGLISH KEYWORD LEXICON (supplementary, not a full model)
# NOTE: This is a small starter list. For production or thesis-grade accuracy,
# expand this using a published Bangla abusive-language dataset.
BANGLA_TOXIC_WORDS = [
    "baje", "faltu", "boka", "pagol", "chagol", "gadha", "murkho",
    "beyadob", "shoytan", "boka chele", "boka meye", "বোকা", "গাধা",
    "পাগল", "খারাপ", "অসভ্য", "বেয়াদব"
]


def clean_text(text):
    """Lowercase, strip URLs, digits, and punctuation from input text."""
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text


def check_bangla_toxic(text):
    """Return list of Bangla/Banglish lexicon words found in the text."""
    text_lower = str(text).lower()
    found = [w for w in BANGLA_TOXIC_WORDS if w in text_lower]
    return found


def password_strength(password):
    """
    Score a password from 0-5 based on length and character variety.
    Returns (score, label, color).
    """
    if not password:
        return 0, "", "#2c2f3a"
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


def highlight_text(original_text, toxic_words):
    """Wrap occurrences of toxic_words in <mark> tags, HTML-escaping the rest."""
    escaped = html.escape(original_text)
    for w in toxic_words:
        pattern = re.compile(rf'\b({re.escape(w)})\b', re.IGNORECASE)
        escaped = pattern.sub(r"<mark>\1</mark>", escaped)
    return escaped


def extract_youtube_video_id(url_or_id):
    """Extract a YouTube video ID from a full URL, or return the input if
    it already looks like a bare video ID."""
    if "youtu.be/" in url_or_id:
        return url_or_id.split("youtu.be/")[1].split("?")[0]
    if "v=" in url_or_id:
        return url_or_id.split("v=")[1].split("&")[0]
    return url_or_id.strip()
