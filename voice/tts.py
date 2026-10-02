"""Lazy adapter for the existing IndicF5 Transformers implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

from .asr_router import ASRRouter, INDIAN_LANGUAGE_CODES, LANGUAGE_LABELS


class TTSUnavailableError(RuntimeError):
    """Raised when a local text-to-speech model cannot be loaded or used."""


class IndicParlerTTS:
    """Lazy multilingual speech synthesis using the local Indic Parler checkpoint."""

    SUPPORTED_LANGUAGES = frozenset({"en", *INDIAN_LANGUAGE_CODES})
    EXPERIMENTAL_LANGUAGES = frozenset({"ks", "pa"})

    def __init__(self, model_dir: str | Path, device: str | None = None) -> None:
        self.model_dir = Path(model_dir)
        self.device = device
        self._model: Any = None
        self._prompt_tokenizer: Any = None
        self._description_tokenizer: Any = None

    def load(self) -> "IndicParlerTTS":
        if self._model is not None:
            return self
        if not (self.model_dir / "config.json").is_file() or not (self.model_dir / "model.safetensors").is_file():
            raise TTSUnavailableError(f"Indic Parler checkpoint not found under {self.model_dir}")
        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer

            self.device = self.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                str(self.model_dir), local_files_only=True
            ).to(self.device).eval()
            self._prompt_tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir), local_files_only=True
            )
            description_model = self._model.config.text_encoder._name_or_path
            self._description_tokenizer = AutoTokenizer.from_pretrained(
                description_model, local_files_only=True
            )
        except Exception as exc:
            self.unload()
            raise TTSUnavailableError(f"Indic Parler failed to load: {exc}") from exc
        return self

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        language: str | None = None,
    ) -> Path:
        if not text or not text.strip():
            raise ValueError("TTS text cannot be empty.")
        selected_language = ASRRouter.language_code(language or "en")
        if selected_language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported Indic Parler language: {language}")
        if self._model is None:
            self.load()
        try:
            import numpy as np
            import soundfile as sf
            import torch

            description = self._description_tokenizer(
                self._description_for_language(selected_language), return_tensors="pt"
            ).to(self.device)
            prompt = self._prompt_tokenizer(text.strip(), return_tensors="pt").to(self.device)
            with torch.inference_mode():
                audio = self._model.generate(
                    input_ids=description.input_ids,
                    attention_mask=description.attention_mask,
                    prompt_input_ids=prompt.input_ids,
                    prompt_attention_mask=prompt.attention_mask,
                    max_new_tokens=512,
                    do_sample=False,
                ).cpu().numpy().squeeze()
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(
                str(output),
                np.asarray(audio, dtype=np.float32),
                samplerate=int(self._model.config.sampling_rate),
            )
            return output
        except Exception as exc:
            raise TTSUnavailableError(f"Indic Parler synthesis failed: {exc}") from exc

    @staticmethod
    def _description_for_language(language: str) -> str:
        language_name = LANGUAGE_LABELS[language]
        return (
            f"A clear female speaker speaks {language_name} slowly in a calm, warm, conversational tone. "
            "The recording is clean and close to the microphone."
        )

    def unload(self) -> None:
        self._model = None
        self._prompt_tokenizer = None
        self._description_tokenizer = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


class IndicF5TTS:
    def __init__(self, model_dir: str | Path, reference_audio: str | Path, reference_text: str, device: str | None = None) -> None:
        self.model_dir = Path(model_dir)
        self.reference_audio = Path(reference_audio)
        self.reference_text = reference_text
        self.device = device
        self._model: Any = None

    def load(self) -> "IndicF5TTS":
        if not self.model_dir.exists():
            raise TTSUnavailableError(f"IndicF5 model directory not found: {self.model_dir}")
        if not self.reference_audio.exists():
            raise TTSUnavailableError(f"IndicF5 reference audio not found: {self.reference_audio}")
        try:
            model_path = str(self.model_dir.resolve())
            if model_path not in sys.path:
                sys.path.insert(0, model_path)
            from transformers import AutoModel
            kwargs: dict[str, Any] = {"trust_remote_code": True, "local_files_only": True}
            if self.device:
                kwargs["device_map"] = self.device
            self._model = AutoModel.from_pretrained(str(self.model_dir), **kwargs)
            if hasattr(self._model, "eval"):
                self._model.eval()
        except Exception as exc:
            raise TTSUnavailableError(f"IndicF5 failed to load: {exc}") from exc
        return self

    def synthesize(self, text: str, output_path: str | Path, language: str | None = None) -> Path:
        if not text or not text.strip():
            raise ValueError("TTS text cannot be empty.")
        if self._model is None:
            self.load()
        try:
            import numpy as np
            import soundfile as sf
            audio = self._model(
                text.strip(),
                ref_audio_path=str(self.reference_audio),
                ref_text=self.reference_text,
            )
            if getattr(audio, "dtype", None) == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output), np.asarray(audio, dtype=np.float32), samplerate=24000)
            return output
        except Exception as exc:
            raise TTSUnavailableError(f"IndicF5 synthesis failed: {exc}") from exc

    def unload(self) -> None:
        self._model = None
