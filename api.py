import os
import pickle
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Optional
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils import clean_text, check_bangla_toxic

BASE_DIR = os.path.dirname(__file__)
MODEL_VERSION = os.getenv("MODEL_VERSION", "hybrid-tfidf-rules-v2.0")
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "cyberbullying_model.pkl"))
VECTORIZER_PATH = os.getenv(
    "VECTORIZER_PATH", os.path.join(BASE_DIR, "tfidf_vectorizer.pkl")
)
TRANSFORMER_MODEL_NAME = os.getenv("TRANSFORMER_MODEL_NAME", "").strip()

app = FastAPI(
    title="Cyberbullying Detection API",
    description="Submit text and receive a cyberbullying classification with confidence score.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = pickle.load(open(MODEL_PATH, "rb"))
vectorizer = pickle.load(open(VECTORIZER_PATH, "rb"))
transformer_classifier = None
transformer_error = None
if TRANSFORMER_MODEL_NAME:
    try:
        from transformers import pipeline

        transformer_classifier = pipeline(
            "text-classification", model=TRANSFORMER_MODEL_NAME
        )
    except Exception as exc:  # Keep the tested local model available as fallback.
        transformer_error = str(exc)


class TextInput(BaseModel):
    text: str


class PredictionResponse(BaseModel):
    text: str
    prediction: str
    confidence: float
    bangla_keywords_flagged: list
    category: str
    risk_level: str
    reasons: list[str]
    model_version: str


class YouTubeProtectionRequest(BaseModel):
    video_id: str
    api_key: str
    max_comments: int = 30
    auto_remove: bool = False
    oauth_access_token: Optional[str] = None


class YouTubeCommentResult(BaseModel):
    comment_id: str
    author: str
    text: str
    prediction: str
    confidence: float
    category: str
    risk_level: str
    reasons: list[str]
    model_version: str
    removed: bool = False


class YouTubeProtectionResponse(BaseModel):
    checked: int
    flagged: int
    removed: int
    comments: list[YouTubeCommentResult]


@app.get("/")
def root():
    return {
        "message": "Cyberbullying Detection API is running. See /docs for usage.",
        "features": ["prediction", "bangla keyword check", "YouTube protection"],
    }


@app.get("/model/info")
def model_info():
    return {
        "version": MODEL_VERSION,
        "engine": "transformer-hybrid" if transformer_classifier else "tfidf-rules-hybrid",
        "transformer_model": TRANSFORMER_MODEL_NAME or None,
        "transformer_ready": transformer_classifier is not None,
        "fallback_active": bool(TRANSFORMER_MODEL_NAME and not transformer_classifier),
        "load_error": transformer_error,
    }


DETECTION_RULES = {
    "Self-harm encouragement": [r"kill yourself", r"kys", r"slit your wrist", r"মরে যা"],
    "Threat": [r"i(?:'ll| will) (?:hurt|kill|beat)", r"you will die", r"watch your back", r"মেরে ফেল", r"মারব"],
    "Hate speech": [r"wipeout", r"exterminate", r"go back to your country", r"all .* are (?:dirty|evil)"],
    "Sexual harassment": [r"slut", r"whore", r"send nudes", r"rape"],
    "Body shaming": [r"fat pig", r"ugly", r"too fat", r"too skinny"],
    "Insult": [r"stupid", r"idiot", r"moron", r"dumb", r"loser", r"nobody likes you", r"বোকা", r"গাধা", r"অসভ্য"],
}


def explain_text(text: str, bangla_hits: list[str], aggressive_emojis: list[str], hostile_emojis: list[str]):
    lowered = text.lower()
    matches = []
    category = "General harassment"
    for label, patterns in DETECTION_RULES.items():
        found = [m.group(0) for pattern in patterns if (m := re.search(pattern, lowered, re.IGNORECASE))]
        if found and not matches:
            category = label
        matches.extend(found)
    matches.extend(bangla_hits)
    matches.extend(aggressive_emojis)
    if len(hostile_emojis) >= 2:
        matches.extend(hostile_emojis)
    return category, list(dict.fromkeys(matches))


def analyze_text(text: str):
    cleaned = clean_text(text)
    vec = vectorizer.transform([cleaned])
    pred = int(model.predict(vec)[0])
    bullying_probability = float(model.predict_proba(vec)[0][1])
    if transformer_classifier is not None:
        transformer_result = transformer_classifier(text, truncation=True)[0]
        label = str(transformer_result.get("label", "")).lower()
        score = float(transformer_result.get("score", 0.0))
        transformer_probability = score if (
            "toxic" in label or label in {"label_1", "1"}
        ) else 1 - score
        bullying_probability = max(bullying_probability, transformer_probability)
        pred = int(bullying_probability >= 0.5)
    # The original model was trained mostly on words.  Add a small, explainable
    # signal for clearly abusive/threatening emoji combinations without treating
    # every negative emoji as bullying.
    aggressive_emojis = re.findall(r"[🖕🔪🔫💣☠💀]", text)
    hostile_emojis = re.findall(r"[😡🤬👿😈]", text)
    bangla_hits = check_bangla_toxic(text)
    category, reasons = explain_text(text, bangla_hits, aggressive_emojis, hostile_emojis)
    if aggressive_emojis or len(hostile_emojis) >= 2 or bangla_hits:
        bullying_probability = max(bullying_probability, 0.82)
        pred = 1
    if reasons and pred == 0:
        bullying_probability = max(bullying_probability, 0.76)
        pred = 1
    confidence = bullying_probability if pred == 1 else 1 - bullying_probability
    if pred == 0:
        category, reasons, risk_level = "Safe", [], "Low"
    elif category in {"Threat", "Self-harm encouragement"}:
        risk_level = "Critical"
    elif confidence >= 0.85 or category in {"Hate speech", "Sexual harassment"}:
        risk_level = "High"
    elif confidence >= 0.65:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    if pred == 1 and not reasons:
        reasons = ["ML model detected a harmful language pattern"]
    return pred, confidence, bangla_hits, category, risk_level, reasons


@app.post("/predict", response_model=PredictionResponse)
def predict(input: TextInput):
    if not input.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    pred, confidence, bangla_hits, category, risk_level, reasons = analyze_text(input.text)

    return PredictionResponse(
        text=input.text,
        prediction="Cyberbullying" if pred == 1 else "Safe",
        confidence=round(confidence, 4),
        bangla_keywords_flagged=bangla_hits,
        category=category,
        risk_level=risk_level,
        reasons=reasons,
        model_version=MODEL_VERSION,
    )


def youtube_json(url: str, *, method: str = "GET", access_token: Optional[str] = None):
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(url, method=method, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"YouTube API error: {detail[:300]}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="Could not reach the YouTube API") from exc


@app.post("/youtube/protect", response_model=YouTubeProtectionResponse)
def protect_youtube(request: YouTubeProtectionRequest):
    """Analyze top-level comments and optionally remove flagged comments.

    Removal requires a short-lived OAuth access token belonging to the channel
    owner and granted the YouTube force-ssl scope. Tokens are never persisted.
    """
    if not request.video_id.strip() or not request.api_key.strip():
        raise HTTPException(status_code=400, detail="video_id and api_key are required")
    if request.auto_remove and not request.oauth_access_token:
        raise HTTPException(status_code=400, detail="OAuth access token is required for removal")

    params = urlencode({
        "part": "snippet",
        "videoId": request.video_id.strip(),
        "maxResults": max(1, min(request.max_comments, 100)),
        "textFormat": "plainText",
        "key": request.api_key.strip(),
    })
    payload = youtube_json(f"https://www.googleapis.com/youtube/v3/commentThreads?{params}")
    results = []
    flagged = 0
    removed = 0

    for item in payload.get("items", []):
        comment = item.get("snippet", {}).get("topLevelComment", {})
        snippet = comment.get("snippet", {})
        comment_id = str(comment.get("id", ""))
        text = str(snippet.get("textDisplay", ""))
        pred, confidence, _, category, risk_level, reasons = analyze_text(text)
        was_removed = False
        if pred == 1:
            flagged += 1
            if request.auto_remove and comment_id:
                delete_url = "https://www.googleapis.com/youtube/v3/comments?" + urlencode({"id": comment_id})
                youtube_json(delete_url, method="DELETE", access_token=request.oauth_access_token)
                removed += 1
                was_removed = True
        results.append(YouTubeCommentResult(
            comment_id=comment_id,
            author=str(snippet.get("authorDisplayName", "Unknown")),
            text=text,
            prediction="Cyberbullying" if pred == 1 else "Safe",
            confidence=round(confidence, 4),
            category=category,
            risk_level=risk_level,
            reasons=reasons,
            model_version=MODEL_VERSION,
            removed=was_removed,
        ))

    return YouTubeProtectionResponse(
        checked=len(results),
        flagged=flagged,
        removed=removed,
        comments=results,
    )
