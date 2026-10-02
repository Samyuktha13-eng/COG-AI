"""Azure Speech REST client for supported Indic locales and English."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


ASR_LOCALES = {
    "as": "as-IN",
    "bn": "bn-IN",
    "en": "en-IN",
    "gu": "gu-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "ne": "ne-NP",
    "or": "or-IN",
    "pa": "pa-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ur": "ur-IN",
}

TTS_VOICES = {
    "as": ("as-IN", "as-IN-YashicaNeural"),
    "bn": ("bn-IN", "bn-IN-TanishaaNeural"),
    "en": ("en-IN", "en-IN-NeerjaNeural"),
    "gu": ("gu-IN", "gu-IN-DhwaniNeural"),
    "hi": ("hi-IN", "hi-IN-SwaraNeural"),
    "kn": ("kn-IN", "kn-IN-SapnaNeural"),
    "ml": ("ml-IN", "ml-IN-SobhanaNeural"),
    "mr": ("mr-IN", "mr-IN-AarohiNeural"),
    "ne": ("ne-NP", "ne-NP-HemkalaNeural"),
    "or": ("or-IN", "or-IN-SubhasiniNeural"),
    "pa": ("pa-IN", "pa-IN-VaaniNeural"),
    "ta": ("ta-IN", "ta-IN-PallaviNeural"),
    "te": ("te-IN", "te-IN-ShrutiNeural"),
    "ur": ("ur-IN", "ur-IN-GulNeural"),
}


class AzureSpeechError(RuntimeError):
    """Raised when an Azure Speech request cannot be completed."""


class AzureSpeechClient:
    """Small synchronous REST client; callers should run it off the event loop."""

    ASR_LOCALES = ASR_LOCALES
    TTS_VOICES = TTS_VOICES

    def __init__(self, key: str = "", region: str = "") -> None:
        self.key = key.strip()
        self.region = region.strip().lower()
        if self.region and not re.fullmatch(r"[a-z0-9-]+", self.region):
            raise ValueError("Azure Speech region must contain only letters, numbers, and hyphens.")

    @classmethod
    def from_environment(cls) -> "AzureSpeechClient":
        return cls(
            key=os.getenv("AZURE_SPEECH_KEY", ""),
            region=os.getenv("AZURE_SPEECH_REGION", ""),
        )

    @property
    def configured(self) -> bool:
        return bool(self.key and self.region)

    def transcribe(self, audio_path: str | Path, language: str) -> dict[str, str | None]:
        if not self.configured:
            raise AzureSpeechError("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to enable Azure Speech.")
        language_code = language.strip().lower()
        locale = ASR_LOCALES.get(language_code)
        if locale is None:
            raise ValueError(f"Azure Speech does not support ASR language: {language}")

        endpoint = f"https://{self.region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
        url = f"{endpoint}?{urlencode({'language': locale, 'format': 'simple'})}"
        request = Request(
            url,
            data=Path(audio_path).read_bytes(),
            headers={
                "Accept": "application/json",
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Ocp-Apim-Subscription-Key": self.key,
            },
            method="POST",
        )
        payload = json.loads(self._send(request, timeout=45).decode("utf-8"))
        transcript = payload.get("DisplayText", "") if payload.get("RecognitionStatus") == "Success" else ""
        return {
            "text": str(transcript).strip(),
            "language": language_code,
            "engine": "azure-speech",
            "model": "speech-to-text",
        }

    def synthesize(self, text: str, language: str) -> bytes:
        if not self.configured:
            raise AzureSpeechError("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to enable Azure Speech.")
        language_code = language.strip().lower()
        voice = TTS_VOICES.get(language_code)
        if voice is None:
            raise ValueError(f"Azure Speech does not support TTS language: {language}")
        if not text.strip():
            raise ValueError("TTS text cannot be empty.")

        locale, voice_name = voice
        safe_text = escape(text.strip())
        ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">'
            f'<voice name="{voice_name}"><prosody rate="-10%">{safe_text}</prosody></voice></speak>'
        )
        request = Request(
            f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1",
            data=ssml.encode("utf-8"),
            headers={
                "Content-Type": "application/ssml+xml",
                "Ocp-Apim-Subscription-Key": self.key,
                "User-Agent": "Cogniv-AI",
                "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            },
            method="POST",
        )
        return self._send(request, timeout=45)

    @staticmethod
    def _send(request: Request, timeout: int) -> bytes:
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise AzureSpeechError(f"Azure Speech returned HTTP {exc.code}.") from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise AzureSpeechError("Could not reach Azure Speech. Check the connection and resource region.") from exc