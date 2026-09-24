"""Adapter for the local IndicConformer INT8 runtime."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .audio import load_audio, prepare_for_asr


class ASRUnavailableError(RuntimeError):
    """Raised when the local IndicConformer runtime cannot be loaded."""


class IndicConformerASR:
    """Load IndicConformer once and reuse it for file transcriptions."""

    def __init__(self, checkpoint_dir: str | Path, language: str = "Hindi", decoding: str = "ctc") -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.language = language
        self.decoding = decoding
        self._engine: Any = None
        self._runtime: Any = None

    @staticmethod
    def _language_code(language: str) -> str:
        aliases = {
            "english": "en",
            "assamese": "as", "bengali": "bn", "bodo": "brx", "dogri": "doi",
            "gujarati": "gu", "hindi": "hi", "kannada": "kn", "kashmiri": "ks",
            "konkani": "kok", "maithili": "mai", "malayalam": "ml", "manipuri": "mni",
            "marathi": "mr", "nepali": "ne", "odia": "or", "punjabi": "pa",
            "sanskrit": "sa", "santali": "sat", "sindhi": "sd", "tamil": "ta",
            "telugu": "te", "urdu": "ur",
        }
        return aliases.get(language.strip().lower(), language.strip().lower())

    def _runtime_path(self) -> Path:
        configured = os.environ.get("INDIC_CONFORMER_RUNTIME")
        candidates = [Path(configured)] if configured else []
        candidates.extend(Path.home().glob(".cache/huggingface/hub/models--ai4bharat--indic-conformer-600m-multilingual/snapshots/*/model_onnx.py"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise ASRUnavailableError(
            "The local checkpoint is complete, but the official IndicConformer model_onnx.py runtime glue "
            "was not found. Set INDIC_CONFORMER_RUNTIME to that file or provide the cached base-model glue."
        )

    def load(self) -> "IndicConformerASR":
        if self._engine is not None:
            return self
        if not self.checkpoint_dir.exists():
            raise ASRUnavailableError(f"IndicConformer checkpoint not found: {self.checkpoint_dir}")
        try:
            runtime_path = self._runtime_path()
            spec = importlib.util.spec_from_file_location("cogniv_indic_conformer_runtime", runtime_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Unable to load runtime module: {runtime_path}")
            runtime = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runtime)
            config = runtime.IndicASRConfig(ts_folder=str(self.checkpoint_dir))
            self._engine = runtime.IndicASRModel(config)
            self._runtime = runtime
        except Exception as exc:
            raise ASRUnavailableError(f"IndicConformer failed to load: {exc}") from exc
        return self

    def transcribe(self, audio: str | Path | Any, language: str | None = None) -> dict[str, Any]:
        if self._engine is None:
            self.load()
        if isinstance(audio, (str, Path)):
            samples, sample_rate = load_audio(audio)
        else:
            samples, sample_rate = audio
        samples, sample_rate = prepare_for_asr(samples, sample_rate)
        selected_language = language or self.language
        language_code = self._language_code(selected_language)
        if language_code not in self._engine.language_masks:
            raise ValueError(
                f"Language '{selected_language}' ({language_code}) is not available in this local "
                "IndicConformer checkpoint. Available codes: "
                + ", ".join(sorted(self._engine.language_masks))
            )
        waveform = torch.from_numpy(np.asarray(samples, dtype=np.float32)).unsqueeze(0)
        try:
            with torch.inference_mode():
                if self.decoding == "ctc":
                    encoder_outputs, encoded_lengths = self._engine.encode(waveform)
                    logits = self._engine.models["ctc_decoder"].run(
                        ["logprobs"], {"encoder_output": encoder_outputs}
                    )[0]
                    logits = torch.from_numpy(logits[:, :, self._engine.language_masks[language_code]])
                    logprobs = logits.log_softmax(dim=-1)
                    path = logprobs[0].argmax(dim=-1)
                    blank_id = self._engine.config.BLANK_ID
                    text = "".join(
                        self._engine.vocab[language_code][index]
                        for index in torch.unique_consecutive(path)
                        if int(index) != blank_id
                    ).replace("▁", " ").strip()
                    active = path != blank_id
                    confidence = float(logprobs[0].max(dim=-1).values[active].exp().mean()) if active.any() else 0.0
                elif self.decoding == "rnnt":
                    text = self._engine._rnnt_decode(*self._engine.encode(waveform), language_code)
                    confidence = None
                else:
                    raise ValueError(f"Unsupported decoding mode: {self.decoding}")
        except Exception as exc:
            raise ASRUnavailableError(f"IndicConformer inference failed: {exc}") from exc
        return {"text": text, "language": selected_language, "confidence": confidence, "model": "indic-conformer-600m-int8"}

    def unload(self) -> None:
        if self._engine is not None:
            del self._engine
        self._engine = None
        self._runtime = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
