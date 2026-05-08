"""
classifier.py
─────────────────────────────────────────────────────────────────────────────
Hybrid NLP pre-classifier for the call center analysis pipeline.

Runs three lightweight Hugging Face inference pipelines (PyTorch backend):
  • Sentiment  → positive / negative / neutral
  • Intent     → complaint / request / information / other
  • Priority   → low / medium / high

Results are injected into the LLM prompt to improve analysis quality.
All classifiers are loaded once at module import time (singleton pattern)
to minimise per-request latency.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Optional import guard – if transformers / torch are not installed the rest
# of the application still works; classify_transcript() returns safe defaults.
# ─────────────────────────────────────────────────────────────────────────────
try:
    from transformers import pipeline as hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "[classifier] `transformers` not installed. "
        "Run: pip install transformers torch  — falling back to defaults."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClassifierResult:
    sentiment: str   # positive | negative | neutral
    intent:    str   # complaint | request | information | other
    priority:  str   # low | medium | high
    confidence: dict # raw confidence scores per dimension (for logging/debug)


# ─────────────────────────────────────────────────────────────────────────────
# Label-mapping helpers
# ─────────────────────────────────────────────────────────────────────────────

_SENTIMENT_MAP: dict[str, str] = {
    # cardiffnlp/twitter-roberta-base-sentiment-latest
    "positive": "positive",
    "negative": "negative",
    "neutral":  "neutral",
    # distilbert-base-uncased-finetuned-sst-2-english (binary)
    "POSITIVE": "positive",
    "NEGATIVE": "negative",
    # generic fallback
    "label_0": "negative",
    "label_1": "neutral",
    "label_2": "positive",
}

# Zero-shot candidate labels for intent & priority
_INTENT_LABELS    = ["complaint", "request for information", "service request", "general inquiry"]
_PRIORITY_LABELS  = ["urgent problem requiring immediate help", "moderate issue", "low priority general question"]

_INTENT_BUCKET: dict[str, str] = {
    "complaint":                          "complaint",
    "request for information":            "information",
    "service request":                    "request",
    "general inquiry":                    "other",
}

_PRIORITY_BUCKET: dict[str, str] = {
    "urgent problem requiring immediate help": "high",
    "moderate issue":                          "medium",
    "low priority general question":           "low",
}


def _map_sentiment(raw_label: str) -> str:
    return _SENTIMENT_MAP.get(raw_label, _SENTIMENT_MAP.get(raw_label.upper(), "neutral"))


def _map_intent(raw_label: str) -> str:
    return _INTENT_BUCKET.get(raw_label.lower(), "other")


def _map_priority(raw_label: str) -> str:
    return _PRIORITY_BUCKET.get(raw_label.lower(), "medium")


# ─────────────────────────────────────────────────────────────────────────────
# Singleton pipeline loaders  (lru_cache → loaded once per process)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_sentiment_pipeline():
    """
    cardiffnlp/twitter-roberta-base-sentiment-latest
    ~125 MB, 3-class (positive / neutral / negative), fast CPU inference.
    Falls back to distilbert SST-2 (binary) if primary download fails.
    """
    primary = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    fallback = "distilbert-base-uncased-finetuned-sst-2-english"
    for model_id in (primary, fallback):
        try:
            logger.info("[classifier] Loading sentiment model: %s", model_id)
            pipe = hf_pipeline(
                "sentiment-analysis",
                model=model_id,
                device=-1,          # CPU
                truncation=True,
                max_length=512,
            )
            logger.info("[classifier] Sentiment model ready: %s", model_id)
            return pipe
        except Exception as exc:  # noqa: BLE001
            logger.warning("[classifier] Could not load %s: %s", model_id, exc)
    return None


@lru_cache(maxsize=1)
def _get_zero_shot_pipeline():
    """
    facebook/bart-large-mnli – zero-shot classification.
    Used for both intent and priority detection.
    ~400 MB; loaded once; shared across both tasks.
    """
    model_id = "facebook/bart-large-mnli"
    try:
        logger.info("[classifier] Loading zero-shot model: %s", model_id)
        pipe = hf_pipeline(
            "zero-shot-classification",
            model=model_id,
            device=-1,
        )
        logger.info("[classifier] Zero-shot model ready.")
        return pipe
    except Exception as exc:  # noqa: BLE001
        logger.warning("[classifier] Could not load zero-shot model: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based fallback (no model)
# ─────────────────────────────────────────────────────────────────────────────

def _rule_based_sentiment(text: str) -> str:
    lowered = text.lower()
    positive_kw = {"thank", "great", "excellent", "happy", "resolved", "appreciate", "pleased"}
    negative_kw = {"complaint", "angry", "unacceptable", "terrible", "never", "awful", "frustrated", "issue"}
    pos = sum(1 for w in positive_kw if w in lowered)
    neg = sum(1 for w in negative_kw if w in lowered)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _rule_based_intent(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in ("complain", "complaint", "angry", "unacceptable", "terrible")):
        return "complaint"
    if any(w in lowered for w in ("how", "what", "when", "where", "why", "tell me", "explain")):
        return "information"
    if any(w in lowered for w in ("please", "could you", "can you", "i need", "i want", "request")):
        return "request"
    return "other"


def _rule_based_priority(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in ("urgent", "immediately", "emergency", "asap", "critical", "right now")):
        return "high"
    if any(w in lowered for w in ("soon", "important", "concerned", "issue", "problem")):
        return "medium"
    return "low"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

_FALLBACK_RESULT = ClassifierResult(
    sentiment="neutral",
    intent="other",
    priority="medium",
    confidence={},
)


def classify_transcript(text: str, max_chars: int = 1024) -> ClassifierResult:
    """
    Run sentiment, intent, and priority classification on *text*.

    Parameters
    ----------
    text:      The raw call-center transcript (or a portion of it).
    max_chars: Truncation limit fed into the models (default 1 024).

    Returns
    -------
    ClassifierResult  — always succeeds; falls back gracefully on error.
    """
    if not text or not text.strip():
        return _FALLBACK_RESULT

    # Truncate to avoid OOM / slow inference on huge transcripts
    snippet = text.strip()[:max_chars]

    if not _TRANSFORMERS_AVAILABLE:
        # Pure rule-based path when transformers isn't installed
        return ClassifierResult(
            sentiment=_rule_based_sentiment(snippet),
            intent=_rule_based_intent(snippet),
            priority=_rule_based_priority(snippet),
            confidence={"source": "rule_based"},
        )

    t0 = time.perf_counter()
    confidence: dict = {}

    # ── Sentiment ────────────────────────────────────────────────────────────
    sentiment = "neutral"
    try:
        sent_pipe = _get_sentiment_pipeline()
        if sent_pipe is not None:
            result = sent_pipe(snippet)[0]
            sentiment = _map_sentiment(result["label"])
            confidence["sentiment_score"] = round(result["score"], 4)
        else:
            sentiment = _rule_based_sentiment(snippet)
            confidence["sentiment_source"] = "rule_based"
    except Exception as exc:  # noqa: BLE001
        logger.warning("[classifier] Sentiment inference failed: %s — using rule-based.", exc)
        sentiment = _rule_based_sentiment(snippet)
        confidence["sentiment_source"] = "rule_based_fallback"

    # ── Intent & Priority (shared zero-shot pipeline) ────────────────────────
    intent   = "other"
    priority = "medium"
    try:
        zs_pipe = _get_zero_shot_pipeline()
        if zs_pipe is not None:
            # Intent
            intent_out = zs_pipe(snippet, candidate_labels=_INTENT_LABELS, multi_label=False)
            top_intent = intent_out["labels"][0]
            intent = _map_intent(top_intent)
            confidence["intent_score"] = round(intent_out["scores"][0], 4)

            # Priority
            prio_out = zs_pipe(snippet, candidate_labels=_PRIORITY_LABELS, multi_label=False)
            top_prio = prio_out["labels"][0]
            priority = _map_priority(top_prio)
            confidence["priority_score"] = round(prio_out["scores"][0], 4)
        else:
            intent   = _rule_based_intent(snippet)
            priority = _rule_based_priority(snippet)
            confidence["zero_shot_source"] = "rule_based"
    except Exception as exc:  # noqa: BLE001
        logger.warning("[classifier] Zero-shot inference failed: %s — using rule-based.", exc)
        intent   = _rule_based_intent(snippet)
        priority = _rule_based_priority(snippet)
        confidence["zero_shot_source"] = "rule_based_fallback"

    elapsed = round(time.perf_counter() - t0, 3)
    confidence["elapsed_seconds"] = elapsed
    logger.info(
        "[classifier] Done in %.3fs → sentiment=%s intent=%s priority=%s",
        elapsed, sentiment, intent, priority,
    )

    return ClassifierResult(
        sentiment=sentiment,
        intent=intent,
        priority=priority,
        confidence=confidence,
    )
