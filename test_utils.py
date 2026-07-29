"""
test_utils.py - Unit tests for utils.py

Run with:
    python3 -m pip install pytest
    python3 -m pytest test_utils.py -v
"""

from utils import (
    clean_text,
    check_bangla_toxic,
    password_strength,
    highlight_text,
    extract_youtube_video_id,
)


# ---------- clean_text ----------

def test_clean_text_lowercases():
    assert clean_text("HELLO WORLD") == "hello world"


def test_clean_text_removes_urls():
    result = clean_text("check this http://example.com/page out")
    assert "http" not in result
    assert "example.com" not in result


def test_clean_text_removes_digits():
    result = clean_text("abc123 def456")
    assert not any(ch.isdigit() for ch in result)


def test_clean_text_removes_punctuation():
    result = clean_text("wow!!! really??")
    assert "!" not in result
    assert "?" not in result


# ---------- check_bangla_toxic ----------

def test_bangla_toxic_detected():
    hits = check_bangla_toxic("tumi ekta pagol chele")
    assert "pagol" in hits


def test_bangla_toxic_not_found_in_clean_text():
    hits = check_bangla_toxic("ajke valo weather")
    assert hits == []


def test_bangla_toxic_case_insensitive():
    hits = check_bangla_toxic("EKTA FALTU KATHA")
    assert "faltu" in hits


# ---------- password_strength ----------

def test_password_strength_empty():
    score, label, color = password_strength("")
    assert score == 0


def test_password_strength_weak_short():
    score, label, color = password_strength("abc")
    assert label in ["Very weak", "Weak"]


def test_password_strength_strong_mixed():
    score, label, color = password_strength("Abcdef1!")
    assert label in ["Strong", "Very strong"]
    assert score >= 4


# ---------- highlight_text ----------

def test_highlight_text_wraps_toxic_word():
    result = highlight_text("you are stupid", ["stupid"])
    assert "<mark>stupid</mark>" in result


def test_highlight_text_case_insensitive_match():
    result = highlight_text("You are STUPID", ["stupid"])
    assert "<mark>STUPID</mark>" in result


def test_highlight_text_escapes_html():
    result = highlight_text("<script>alert(1)</script> stupid", ["stupid"])
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_highlight_text_no_toxic_words():
    result = highlight_text("hello world", [])
    assert result == "hello world"


# ---------- extract_youtube_video_id ----------

def test_extract_video_id_from_short_url():
    assert extract_youtube_video_id("https://youtu.be/abc123XYZ") == "abc123XYZ"


def test_extract_video_id_from_watch_url():
    url = "https://www.youtube.com/watch?v=abc123XYZ&t=10s"
    assert extract_youtube_video_id(url) == "abc123XYZ"


def test_extract_video_id_already_bare_id():
    assert extract_youtube_video_id("abc123XYZ") == "abc123XYZ"