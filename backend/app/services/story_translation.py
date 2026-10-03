"""Optional Azure Translator adapter for story-evidence matching."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import requests

_LANGUAGE_ALIASES = {"kok": "gom"}
_LANGUAGE_NAMES = {
    "as": "Assamese", "bn": "Bengali", "brx": "Bodo", "doi": "Dogri", "en": "English",
    "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada", "kok": "Konkani", "ks": "Kashmiri",
    "mai": "Maithili", "ml": "Malayalam", "mni": "Manipuri", "mr": "Marathi", "ne": "Nepali",
    "or": "Odia", "pa": "Punjabi", "sa": "Sanskrit", "sat": "Santali", "sd": "Sindhi",
    "ta": "Tamil", "te": "Telugu", "ur": "Urdu",
}
_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}
_REVERSE_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}
_CACHE_LIMIT = 512
_GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_GROQ_TRANSLATION_MODEL = "llama-3.3-70b-versatile"


def _normalize_language_code(language: str) -> str:
    return language.lower().split("-")[0]


def _azure_language_code(language: str) -> str:
    return _LANGUAGE_ALIASES.get(language, language)


def _request_azure_translation(text: str, source_language: str, target_language: str) -> str | None:
    key = os.getenv("AZURE_TRANSLATOR_KEY", "").strip()
    if not key or not text.strip() or len(text) > 5000:
        return None

    endpoint = os.getenv(
        "AZURE_TRANSLATOR_ENDPOINT",
        "https://api.cognitive.microsofttranslator.com",
    ).strip().rstrip("/")
    source_code = _azure_language_code(source_language)
    target_code = _azure_language_code(target_language)
    url = f"{endpoint}/translate?{urlencode({'api-version': '3.0', 'from': source_code, 'to': target_code})}"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json; charset=UTF-8",
    }
    region = os.getenv("AZURE_TRANSLATOR_REGION", "").strip()
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region
    request = Request(
        url,
        data=json.dumps([{"Text": text}], ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        translated = payload[0]["translations"][0]["text"].strip()
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None

    return translated or None


def _request_groq_translation(text: str, source_language: str, target_language: str) -> str | None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or not text.strip() or len(text) > 5000:
        return None

    source_name = _LANGUAGE_NAMES.get(source_language, source_language)
    target_name = _LANGUAGE_NAMES.get(target_language, target_language)
    payload = {
        "model": os.getenv("GROQ_TRANSLATION_MODEL", _DEFAULT_GROQ_TRANSLATION_MODEL).strip(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional translator. Translate faithfully and naturally. "
                    "Preserve names, facts, and meaning. Return only the translated text, without quotes, "
                    "labels, explanations, or added details."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Translate from {source_name} ({source_language}) to {target_name} ({target_language}). "
                    f"Keep the output in {target_name}.\n\n{text.strip()}"
                ),
            },
        ],
        "temperature": 0,
        "max_tokens": min(2048, max(256, len(text) * 3)),
    }
    try:
        response = requests.post(
            _GROQ_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None
    return result or None


def _request_translation(text: str, source_language: str, target_language: str) -> str | None:
    """Prefer Groq; use Azure Translator only when Groq is not configured or fails."""
    translated = _request_groq_translation(text, source_language, target_language)
    if translated:
        return translated
    return _request_azure_translation(text, source_language, target_language)


def translate_to_english(text: str, language: str) -> str | None:
    """Translate a short answer to English, returning None when unavailable."""
    source_language = _normalize_language_code(language)
    if source_language == "en":
        return text

    cache_key = (source_language, text)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    translated = _request_translation(text, source_language, "en")
    if not translated:
        return None
    if len(_TRANSLATION_CACHE) >= _CACHE_LIMIT:
        _TRANSLATION_CACHE.clear()
    _TRANSLATION_CACHE[cache_key] = translated
    return translated


def translate_to_language(text: str, language: str) -> str | None:
    """Translate English text into the requested supported language when a local string is missing."""
    target_language = _normalize_language_code(language)
    if target_language == "en" or not text.strip():
        return text

    cache_key = (target_language, text)
    if cache_key in _REVERSE_TRANSLATION_CACHE:
        return _REVERSE_TRANSLATION_CACHE[cache_key]

    translated = _request_translation(text, "en", target_language)
    if not translated:
        return None
    if len(_REVERSE_TRANSLATION_CACHE) >= _CACHE_LIMIT:
        _REVERSE_TRANSLATION_CACHE.clear()
    _REVERSE_TRANSLATION_CACHE[cache_key] = translated
    return translated


class StoryTranslationUnavailableError(RuntimeError):
    """Raised when requested-language story text cannot be produced."""


def require_translation_to_language(text: str, language: str) -> str:
    translated = translate_to_language(text, language)
    if not translated:
        target_language = _normalize_language_code(language)
        raise StoryTranslationUnavailableError(
            f"Translation to '{target_language}' is unavailable. Check Groq or Azure Translator configuration. "
            "English fallback is disabled."
        )
    return translated


def translate_text(text: str, language: str) -> str | None:
    """Backward-compatible alias kept for older callers."""
    return translate_to_language(text, language)
