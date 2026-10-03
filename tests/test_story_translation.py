import io
import json
from urllib.parse import parse_qs, urlparse

from backend.app.services import story_translation


def test_azure_translator_uses_configured_resource_and_konkani_alias(monkeypatch):
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "test-key")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "centralindia")
    monkeypatch.setenv("AZURE_TRANSLATOR_ENDPOINT", "https://translator.example")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    story_translation._TRANSLATION_CACHE.clear()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps([
            {"translations": [{"to": "en", "text": "The patient says jasmine."}]}
        ]).encode("utf-8"))

    monkeypatch.setattr(story_translation, "urlopen", fake_urlopen)

    translated = story_translation.translate_to_english("कोंकणी उत्तर", "kok-IN")

    assert translated == "The patient says jasmine."
    request, timeout = calls[0]
    assert parse_qs(urlparse(request.full_url).query) == {
        "api-version": ["3.0"], "from": ["gom"], "to": ["en"]
    }
    assert request.get_header("Ocp-apim-subscription-key") == "test-key"
    assert request.get_header("Ocp-apim-subscription-region") == "centralindia"
    assert timeout == 4


def test_azure_translator_can_translate_english_to_assamese(monkeypatch):
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "test-key")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "centralindia")
    monkeypatch.setenv("AZURE_TRANSLATOR_ENDPOINT", "https://translator.example")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    story_translation._TRANSLATION_CACHE.clear()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps([
            {"translations": [{"to": "as", "text": "দরজার কাছে লক্ষ্মী কী করছে?"}]}
        ]).encode("utf-8"))

    monkeypatch.setattr(story_translation, "urlopen", fake_urlopen)

    translated = story_translation.translate_to_language("What is Lakshmi doing at the door?", "as")

    assert translated == "দরজার কাছে লক্ষ্মী কী করছে?"
    request, timeout = calls[0]
    assert parse_qs(urlparse(request.full_url).query) == {
        "api-version": ["3.0"], "from": ["en"], "to": ["as"]
    }
    assert request.get_header("Ocp-apim-subscription-key") == "test-key"
    assert request.get_header("Ocp-apim-subscription-region") == "centralindia"
    assert timeout == 4


def test_translator_is_skipped_without_credentials(monkeypatch):
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert story_translation.translate_to_english("respuesta", "es") is None


def test_groq_translates_all_supported_languages_without_azure(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_TRANSLATION_MODEL", "test-model")
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY", raising=False)
    calls = []

    class FakeResponse:
        def __init__(self, language):
            self.language = language

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": f"translated-{self.language}"}}]}

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        user_message = kwargs["json"]["messages"][1]["content"]
        return FakeResponse(user_message.split("(")[-1].split(")")[0])

    monkeypatch.setattr(story_translation.requests, "post", fake_post)
    story_translation._REVERSE_TRANSLATION_CACHE.clear()

    for language, name in story_translation._LANGUAGE_NAMES.items():
        if language == "en":
            continue
        translated = story_translation.translate_to_language(f"Question for {language}", language)
        assert translated == f"translated-{language}"
        request_url, kwargs = calls[-1]
        assert request_url == story_translation._GROQ_CHAT_COMPLETIONS_URL
        assert kwargs["headers"]["Authorization"] == "Bearer test-groq-key"
        assert kwargs["json"]["model"] == "test-model"
        assert name in kwargs["json"]["messages"][1]["content"]
        assert kwargs["timeout"] == 20


def test_groq_translation_failure_falls_back_to_english(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("AZURE_TRANSLATOR_KEY", raising=False)
    monkeypatch.setattr(
        story_translation.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(story_translation.requests.Timeout()),
    )

    translated = story_translation.require_translation_to_language("What is Lakshmi doing?", "te")

    assert translated == "What is Lakshmi doing?"