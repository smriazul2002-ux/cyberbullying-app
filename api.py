import os
import pickle
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils import clean_text, check_bangla_toxic

BASE_DIR = os.path.dirname(__file__)

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

model = pickle.load(open(os.path.join(BASE_DIR, "cyberbullying_model.pkl"), "rb"))
vectorizer = pickle.load(open(os.path.join(BASE_DIR, "tfidf_vectorizer.pkl"), "rb"))


class TextInput(BaseModel):
    text: str


class PredictionResponse(BaseModel):
    text: str
    prediction: str
    confidence: float
    bangla_keywords_flagged: list


@app.get("/")
def root():
    return {"message": "Cyberbullying Detection API is running. See /docs for usage."}


@app.post("/predict", response_model=PredictionResponse)
def predict(input: TextInput):
    cleaned = clean_text(input.text)
    vec = vectorizer.transform([cleaned])

    pred = int(model.predict(vec)[0])
    prob = float(model.predict_proba(vec)[0][1])
    bangla_hits = check_bangla_toxic(input.text)

    return PredictionResponse(
        text=input.text,
        prediction="Cyberbullying" if pred == 1 else "Safe",
        confidence=round(prob, 4),
        bangla_keywords_flagged=bangla_hits,
    )
