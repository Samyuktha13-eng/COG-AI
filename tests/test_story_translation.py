import io
import json
from urllib.parse import parse_qs, urlparse

from backend.app.services import story_translation


def test_azure_translator_uses_configured_resource_and_konkani_alias(monkeypatch):
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "test-key")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "centralindia")
    monkeypatch.setenv("AZURE_TRANSLATOR_ENDPOINT", "https://translator.example")
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
    assert story_translation.translate_to_english("respuesta", "es") is None