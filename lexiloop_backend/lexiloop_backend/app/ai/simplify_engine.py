"""
ai/simplify_engine.py — the T5 simplification + readability logic from
Dyslexia Buddy's app.py, extracted so it can be imported by both the
/simplify router and the LangChain agent's "simplify_text" tool,
instead of living inside a FastAPI route.
"""

from __future__ import annotations
import re
import logging
from functools import lru_cache
from typing import Optional

import nltk
import textstat
import torch
from nltk.corpus import wordnet
from nltk.tokenize import sent_tokenize, word_tokenize
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from wordfreq import zipf_frequency

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

for pkg in ("punkt", "punkt_tab", "wordnet", "omw-1.4"):
    try:
        nltk.download(pkg, quiet=True)
    except Exception as exc:
        logger.warning("Could not download %s: %s", pkg, exc)

MODEL_NAME = "t5-small"
HARD_ZIPF_THRESHOLD = 4.0

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "i", "we", "you", "he", "she", "they",
}

_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForSeq2SeqLM] = None
_model_ready = False


def load_model() -> None:
    global _tokenizer, _model, _model_ready
    try:
        logger.info("Loading T5 simplification model...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        _model.eval()
        _model_ready = True
        logger.info("Model loaded successfully.")
    except Exception as exc:
        logger.error("Model failed to load: %s", exc)
        _model_ready = False


def is_model_ready() -> bool:
    return _model_ready


def zipf_score(word: str) -> float:
    return zipf_frequency(word.lower(), "en")


def is_hard_word(word: str) -> bool:
    clean = word.lower()
    if clean in STOPWORDS or len(clean) <= 2:
        return False
    if not re.match(r"^[a-z]+$", clean):
        return False
    return zipf_score(clean) < HARD_ZIPF_THRESHOLD


@lru_cache(maxsize=4096)
def get_synonym(word: str) -> Optional[str]:
    clean = word.lower()
    synsets = wordnet.synsets(clean)
    if not synsets:
        return None

    candidates: list[tuple[str, float]] = []
    for syn in synsets:
        for lemma in syn.lemmas():
            name = lemma.name().replace("_", " ")
            if name.lower() == clean or " " in name or not name.isalpha():
                continue
            candidates.append((name.lower(), zipf_frequency(name.lower(), "en")))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_word, best_score = candidates[0]
    if best_score > zipf_frequency(clean, "en") + 0.3:
        return best_word
    return None


def normalise_text(text: str) -> str:
    text = re.sub(r'[\u2012\u2013\u2014\u2015]', '-', text)
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = re.sub(r'([a-zA-Z])-([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def rule_simplify(text: str) -> str:
    text = normalise_text(text)
    sentences = sent_tokenize(text)
    output: list[str] = []

    for sent in sentences:
        tokens = re.findall(r"[A-Za-z]+|[^A-Za-z]+", sent)
        replaced = []
        for tok in tokens:
            if tok.isalpha() and is_hard_word(tok):
                syn = get_synonym(tok)
                if syn:
                    if tok[0].isupper():
                        syn = syn.capitalize()
                    replaced.append(syn)
                    continue
            replaced.append(tok)

        new_sent = "".join(replaced).strip()
        words_in_sent = new_sent.split()
        if len(words_in_sent) > 15:
            mid = len(words_in_sent) // 2
            best = mid
            for i in range(mid, max(3, mid - 6), -1):
                if words_in_sent[i - 1].endswith(","):
                    best = i
                    break
            part_a = " ".join(words_in_sent[:best]).rstrip(",") + "."
            part_b = " ".join(words_in_sent[best:])
            output.append(part_a)
            output.append(part_b)
        else:
            output.append(new_sent)

    return " ".join(output)


def ml_simplify(text: str) -> str:
    if not _model_ready or _tokenizer is None or _model is None:
        return rule_simplify(text)

    text = normalise_text(text)
    sentences = sent_tokenize(text)
    simplified: list[str] = []

    for sent in sentences:
        prompt = f"summarize: {sent}"
        try:
            inputs = _tokenizer(prompt, return_tensors="pt", max_length=256, truncation=True)
            with torch.no_grad():
                outputs = _model.generate(
                    **inputs, max_new_tokens=128, num_beams=4,
                    early_stopping=True, no_repeat_ngram_size=3,
                )
            decoded = _tokenizer.decode(outputs[0], skip_special_tokens=True)
            decoded = re.sub(r'^simplify:\s*', '', decoded, flags=re.IGNORECASE)
            simplified.append(decoded.strip())
        except Exception as exc:
            logger.warning("T5 inference failed for sentence: %s", exc)
            simplified.append(sent)

    return " ".join(simplified)


def compute_readability(text: str) -> dict:
    fre = round(textstat.flesch_reading_ease(text), 1)
    fkg = round(textstat.flesch_kincaid_grade(text), 1)
    words = word_tokenize(text)
    alpha = [w for w in words if w.isalpha()]
    sents = sent_tokenize(text)
    avg_sl = round(len(alpha) / max(1, len(sents)), 1)
    hard = [w for w in alpha if is_hard_word(w)]

    if fre >= 80:
        label = "Very easy"
    elif fre >= 60:
        label = "Standard"
    elif fre >= 40:
        label = "Difficult"
    else:
        label = "Very hard"

    return {
        "flesch_reading_ease": fre,
        "flesch_kincaid_grade": fkg,
        "avg_sentence_length": avg_sl,
        "hard_word_count": len(hard),
        "hard_word_percent": round(len(hard) / max(1, len(alpha)) * 100, 1),
        "total_words": len(alpha),
        "label": label,
    }
