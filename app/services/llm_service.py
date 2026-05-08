"""
llm_service.py
─────────────────────────────────────────────────────────────────────────────
Hybrid AI analysis pipeline for call-center transcripts.

Flow
────
  1. classify_transcript()  ← classifier.py  (HuggingFace / PyTorch)
       • sentiment  →  positive | negative | neutral
       • intent     →  complaint | request | information | other
       • priority   →  low | medium | high

  2. _build_prompt()        injects NLP results into the LLM prompt

  3. Ollama (LLaMA 3)       returns extended JSON analysis

Output JSON schema
──────────────────
{
  "sentiment":        "...",
  "intent":           "...",
  "priority":         "...",
  "rating":           <1-5>,
  "explanation":      "...",
  "strengths":        ["..."],
  "weaknesses":       ["..."],
  "suggestions":      ["..."],
  "clean_transcript": "..."
}
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from app.services.classifier import ClassifierResult, classify_transcript

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Custom exception
# ─────────────────────────────────────────────────────────────────────────────

class LLMError(Exception):
    """Raised when the LLM analysis step fails unrecoverably."""


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_OLLAMA_URL      = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL           = "llama3"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder  (enriched with NLP pre-classification)
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(text: str, clf: ClassifierResult) -> str:
    """
    Build the LLM prompt, injecting NLP classification results so the model
    can produce a more accurate, context-aware evaluation.
    """
    return f"""
You are an AI Call Quality Analyst specialising in customer service excellence.

── Pre-Classification Results (computed by NLP models, treat as reliable signals) ──
  • Customer Sentiment : {clf.sentiment}
  • Call Intent        : {clf.intent}
  • Priority Level     : {clf.priority}

── Task ────────────────────────────────────────────────────────────────────────────
Analyse the following call-center transcript and produce a structured quality report.

Transcript:
\"\"\"{text}\"\"\"

── Instructions ─────────────────────────────────────────────────────────────────
1. Clean the transcript: fix grammar and spelling errors.
2. Rate the agent's performance from 1 to 5 (integer).
3. Write a concise explanation for the rating (2-4 sentences).
4. List 2-3 agent STRENGTHS observed in the call.
5. List 2-3 agent WEAKNESSES or missed opportunities.
6. Provide 2-3 actionable SUGGESTIONS for improvement.
7. Use the pre-classification signals above to calibrate your analysis:
   - A NEGATIVE sentiment with a HIGH-priority complaint should lower the rating
     unless the agent handled it exceptionally well.
   - A POSITIVE sentiment signals good rapport; reflect that in strengths.
   - Match your tone and advice to the detected intent ({clf.intent}).

── Output Format (strict JSON, no markdown fences) ──────────────────────────────
{{
  "sentiment":        "{clf.sentiment}",
  "intent":           "{clf.intent}",
  "priority":         "{clf.priority}",
  "clean_transcript": "...",
  "rating":           4,
  "explanation":      "...",
  "strengths":        ["...", "..."],
  "weaknesses":       ["...", "..."],
  "suggestions":      ["...", "..."]
}}

Rules:
- Always return VALID JSON with all nine keys.
- Do NOT wrap the JSON in markdown code blocks.
- Keep each list to 2-3 items maximum.
- Be concise but specific.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extract the first complete JSON object from raw LLM output."""
    # Fast path – the whole response is valid JSON
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback – scan for the outermost { … } block
    start = raw_text.find("{")
    end   = raw_text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise LLMError("LLM returned output without a JSON object.")

    json_str = raw_text[start : end + 1]
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"JSON parse failed. Extracted fragment: {json_str[:120]}..."
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMError("LLM JSON response is not a JSON object.")

    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# Output validation & normalisation
# ─────────────────────────────────────────────────────────────────────────────

_VALID_SENTIMENTS = {"positive", "negative", "neutral"}
_VALID_INTENTS    = {"complaint", "request", "information", "other"}
_VALID_PRIORITIES = {"low", "medium", "high"}


def _validate_analysis(
    data: dict[str, Any],
    clf:  ClassifierResult,
    raw_text: str = "",
) -> dict[str, Any]:
    """
    Normalise and validate the parsed LLM JSON.
    Missing or malformed fields are replaced with safe defaults drawn from
    the NLP classifier results so the output is always complete.
    """
    # ── Rating ───────────────────────────────────────────────────────────────
    rating = data.get("rating", 3)
    if isinstance(rating, str):
        try:
            rating = int(re.sub(r"[^0-9]", "", rating))
        except ValueError:
            rating = 3
    elif not isinstance(rating, (int, float)):
        rating = 3
    rating = max(1, min(5, int(rating)))

    # ── NLP fields (prefer LLM output if valid, else trust classifier) ───────
    sentiment = str(data.get("sentiment", clf.sentiment)).lower()
    if sentiment not in _VALID_SENTIMENTS:
        sentiment = clf.sentiment

    intent = str(data.get("intent", clf.intent)).lower()
    if intent not in _VALID_INTENTS:
        intent = clf.intent

    priority = str(data.get("priority", clf.priority)).lower()
    if priority not in _VALID_PRIORITIES:
        priority = clf.priority

    # ── Text fields ──────────────────────────────────────────────────────────
    clean_transcript = data.get("clean_transcript", data.get("transcript", raw_text))
    explanation      = data.get(
        "explanation",
        "The AI model provided an analysis but omitted the explanation.",
    )

    def _safe_list(key: str) -> list[str]:
        val = data.get(key, [])
        if isinstance(val, list):
            return [str(item) for item in val]
        return []

    return {
        "sentiment":        sentiment,
        "intent":           intent,
        "priority":         priority,
        "clean_transcript": str(clean_transcript).strip(),
        "rating":           rating,
        "explanation":      str(explanation).strip(),
        "strengths":        _safe_list("strengths"),
        "weaknesses":       _safe_list("weaknesses"),
        "suggestions":      _safe_list("suggestions"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Fallback  (when Ollama is unreachable or returns garbage)
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_analysis(
    transcript: str,
    clf: ClassifierResult,
    reason: str,
) -> dict[str, Any]:
    """
    Rule-based fallback that still returns the full extended schema.
    Uses the NLP classifier results to make the fallback more meaningful.
    """
    logger.warning("[llm] Returning fallback JSON. Reason: %s", reason)

    lowered = transcript.lower()
    score   = 3

    positive_signals = ["please", "thank you", "thanks", "let me help", "absolutely"]
    negative_signals = ["don't know", "cannot help", "impossible", "not sure"]

    for sig in positive_signals:
        if sig in lowered:
            score += 1
            break
    for sig in negative_signals:
        if sig in lowered:
            score -= 1
            break

    word_count = len(transcript.split())
    if word_count < 12:
        score -= 1
    elif word_count > 60:
        score += 1

    # Adjust score using NLP signals
    if clf.sentiment == "positive":
        score = min(5, score + 1)
    elif clf.sentiment == "negative":
        score = max(1, score - 1)

    if clf.priority == "high" and clf.sentiment == "negative":
        score = max(1, score - 1)

    score = max(1, min(5, score))

    if score >= 4:
        explanation = (
            f"The agent demonstrated reasonably effective communication. "
            f"The customer's {clf.intent} was addressed with a {clf.sentiment} outcome."
        )
    elif score == 3:
        explanation = (
            f"The call showed average performance. "
            f"The {clf.priority}-priority {clf.intent} could have been handled with more precision."
        )
    else:
        explanation = (
            f"The agent struggled with a {clf.priority}-priority {clf.intent}. "
            f"Customer left with a {clf.sentiment} sentiment."
        )

    strengths  = ["Basic communication was established"] if score >= 3 else []
    weaknesses = ["Could improve proactive assistance"]  if score <= 3 else []

    if clf.intent == "complaint":
        weaknesses.append("Complaint resolution process needs reinforcement")
    if clf.priority == "high":
        suggestions = [
            "Escalate high-priority issues immediately to a senior agent.",
            "Use empathetic language to de-escalate tense situations.",
        ]
    else:
        suggestions = [
            "Provide clearer, step-by-step instructions.",
            "Use more empathetic and positive language throughout.",
        ]

    return {
        "sentiment":        clf.sentiment,
        "intent":           clf.intent,
        "priority":         clf.priority,
        "clean_transcript": transcript.strip(),
        "rating":           score,
        "explanation":      explanation,
        "strengths":        strengths,
        "weaknesses":       weaknesses,
        "suggestions":      suggestions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def analyze_text(
    text: str,
    model:           str = DEFAULT_MODEL,
    ollama_url:      str = DEFAULT_OLLAMA_URL,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    Hybrid analysis pipeline:

    Parameters
    ----------
    text            : Raw call-center transcript.
    model           : Ollama model name (default: llama3).
    ollama_url      : Full URL to Ollama generate endpoint.
    timeout_seconds : HTTP timeout for the LLM call.

    Returns
    -------
    dict with keys: sentiment, intent, priority, rating, explanation,
                    strengths, weaknesses, suggestions, clean_transcript.

    Raises
    ------
    LLMError  if Ollama is unreachable (no fallback for server errors).
    """
    if not text or not text.strip():
        raise LLMError("Transcript is empty.")

    transcript = text.strip()

    # ── Step 1: NLP Pre-classification ───────────────────────────────────────
    logger.info("[llm] Running NLP pre-classification …")
    try:
        clf = classify_transcript(transcript)
        logger.info(
            "[llm] Classification → sentiment=%s  intent=%s  priority=%s",
            clf.sentiment, clf.intent, clf.priority,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[llm] Classifier raised an exception: %s — using defaults.", exc)
        from app.services.classifier import ClassifierResult
        clf = ClassifierResult(
            sentiment="neutral",
            intent="other",
            priority="medium",
            confidence={"source": "exception_fallback"},
        )

    # ── Step 2: Health-check Ollama ──────────────────────────────────────────
    health_url = f"{DEFAULT_OLLAMA_BASE_URL}/api/tags"
    try:
        logger.info("[llm] Checking Ollama server at %s …", health_url)
        health_resp = requests.get(health_url, timeout=5)
        health_resp.raise_for_status()
    except requests.RequestException as exc:
        raise LLMError(
            "Ollama server is not reachable. "
            "Start it with `ollama serve` and keep it running."
        ) from exc

    # ── Step 3: Build enriched prompt and call LLM ───────────────────────────
    prompt  = _build_prompt(transcript, clf)
    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "num_ctx":     2048,
            "temperature": 0.2,
            "top_p":       0.9,
        },
    }

    try:
        logger.info("[llm] POST → %s  (model=%s)", ollama_url, model)
        response = requests.post(ollama_url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        logger.error("[llm] LLM request failed: %s", exc)
        raise LLMError("Failed to call the local LLM API.") from exc
    except ValueError as exc:
        logger.error("[llm] LLM returned non-JSON HTTP body: %s", exc)
        raise LLMError("LLM API returned an invalid response payload.") from exc

    raw_output = body.get("response")
    if not isinstance(raw_output, str) or not raw_output.strip():
        raise LLMError("LLM API response is missing the text output field.")

    # ── Step 4: Parse, validate, and return ──────────────────────────────────
    try:
        parsed    = _extract_json_object(raw_output.strip())
        validated = _validate_analysis(parsed, clf, raw_text=transcript)
        validated["transcript"] = transcript          # keep original for callers
        return validated
    except LLMError as exc:
        logger.warning(
            "[llm] Could not parse LLM response (%s). Raw snippet: %s",
            exc,
            raw_output[:300],
        )
        result = _fallback_analysis(transcript, clf, str(exc))
        result["transcript"] = transcript
        return result