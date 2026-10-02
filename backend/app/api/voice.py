"""
Voice API
=========
POST /api/voice/transcribe          — transcribe any audio (generic)
POST /api/voice/caregiver-prompt    — caregiver speaks → ASR → GroundingAgent resolve
                                      (same result as POST /api/grounding/resolve with text)
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask

from ..models.grounding import GroundingResult
from ..services.grounding import GroundingAgent
from voice.azure_speech import AzureSpeechClient, AzureSpeechError
from voice.asr_router import ASRRouter, LANGUAGE_LABELS
from voice.intent import IntentRouter
from voice.tts import IndicParlerTTS, TTSUnavailableError

router = APIRouter(prefix="/api/voice", tags=["voice"])
_intent_router = IntentRouter()
_speech_model_lock = Lock()
_parler_tts: IndicParlerTTS | None = None


def _new_temporary_audio(suffix: str):
    project_root = Path(__file__).resolve().parents[3]
    configured_root = os.getenv("COGNIV_TEMP_DIR", "").strip()
    temp_root = Path(configured_root) if configured_root else project_root / "outputs" / ".runtime-temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    return NamedTemporaryFile(suffix=suffix, delete=False, dir=temp_root)


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """Generic transcription endpoint — returns raw transcript."""
    transcript = await _run_asr(audio, "generic", language)
    if not transcript:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "empty_transcript",
                "message": "No speech was detected in the audio. Please speak clearly and try again.",
            },
        )
    return {"transcript": transcript, "language": language}


@router.get("/capabilities")
def voice_capabilities():
    """Report supported ASR/TTS languages and configured speech runtimes."""
    project_root = Path(__file__).resolve().parents[3]
    capabilities = ASRRouter.capabilities(project_root)
    azure_speech = AzureSpeechClient.from_environment()
    tts_model_dir = project_root / "models" / "indic-parler-tts"
    tts_checkpoint_ready = (
        (tts_model_dir / "config.json").is_file()
        and (tts_model_dir / "model.safetensors").is_file()
    )
    tts_runtime_ready = importlib.util.find_spec("parler_tts") is not None
    local_tts_ready = tts_checkpoint_ready and tts_runtime_ready
    tts_ready = azure_speech.configured or local_tts_ready
    if azure_speech.configured:
        tts_message = "Azure Speech configured. TTS uses the free-tier quota; prompts are sent to Azure."
        tts_provider = "azure-speech"
    elif local_tts_ready:
        tts_message = "Indic Parler checkpoint and runtime are ready."
        tts_provider = "indic-parler-local"
    elif not tts_checkpoint_ready:
        tts_message = f"Indic Parler checkpoint not found under {tts_model_dir}."
        tts_provider = "unavailable"
    else:
        tts_message = "Indic Parler runtime is missing; install the optional parler-tts dependency."
        tts_provider = "unavailable"
    capabilities["engines"]["tts"] = {
        "ready": tts_ready,
        "message": tts_message,
        "provider": tts_provider,
        "languages": [
            {
                "code": code,
                "name": name,
                "ready": (azure_speech.configured and code in azure_speech.TTS_VOICES) or local_tts_ready,
                "support": (
                    "azure-speech"
                    if azure_speech.configured and code in azure_speech.TTS_VOICES
                    else "local-fallback"
                    if azure_speech.configured and local_tts_ready
                    else "experimental"
                    if code in IndicParlerTTS.EXPERIMENTAL_LANGUAGES
                    else "official"
                ),
            }
            for code, name in sorted(LANGUAGE_LABELS.items())
        ],
    }
    return capabilities


@router.post("/synthesize")
async def synthesize_voice(
    text: str = Form(...),
    language: str = Form(default="en"),
):
    """Synthesize speech with Azure Speech when configured, otherwise local Parler."""
    project_root = Path(__file__).resolve().parents[3]
    azure_speech = AzureSpeechClient.from_environment()
    language_code = ASRRouter.language_code(language)
    if azure_speech.configured and language_code in azure_speech.TTS_VOICES:
        try:
            audio = await asyncio.to_thread(azure_speech.synthesize, text, language_code)
            return Response(
                content=audio,
                media_type="audio/wav",
                headers={"Content-Disposition": 'inline; filename="cogniv-speech.wav"'},
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AzureSpeechError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    output_path: Path | None = None
    try:
        with _new_temporary_audio(".wav") as tmp:
            output_path = Path(tmp.name)
        await asyncio.to_thread(_synthesize_with_local_parler, text, output_path, language, project_root)
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename="cogniv-speech.wav",
            background=BackgroundTask(output_path.unlink, missing_ok=True),
        )
    except (ValueError, TTSUnavailableError) as exc:
        if output_path is not None:
            output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        if output_path is not None:
            output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Local speech synthesis failed.") from exc


@router.post("/caregiver-prompt", response_model=GroundingResult)
async def caregiver_voice_prompt(
    patient_id: str = Form(...),
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """
    Caregiver speaks a memory request.
    Pipeline: audio → ASR → GroundingAgent.resolve → GroundingResult

    Identical contract to POST /api/grounding/resolve but accepts voice.
    Returns match=False (200) when no story matches — never invents.
    """
    transcript = await _run_asr(audio, patient_id, language)
    if not transcript:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "empty_transcript",
                "message": "Could not transcribe the audio. Please try again.",
            },
        )
    result = GroundingAgent().resolve(transcript)
    # Attach the transcript so the caller can display what was heard
    result_dict = result.model_dump()
    result_dict["transcript"] = transcript
    return result_dict


@router.post("/command")
async def voice_command(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """Transcribe a spoken app command and classify it without narrating it."""
    transcript = await _run_asr(audio, "command", language)
    if not transcript:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "empty_transcript",
                "message": "Could not hear a command. Please try again.",
            },
        )
    return {
        "transcript": transcript,
        "language": ASRRouter.language_code(language),
        "intent": _intent_router.route(transcript),
    }


# ---------------------------------------------------------------------------
# Shared ASR helper
# ---------------------------------------------------------------------------

def _synthesize_with_local_parler(text: str, output_path: Path, language: str, project_root: Path) -> None:
    global _parler_tts
    with _speech_model_lock:
        if _parler_tts is None:
            _parler_tts = IndicParlerTTS(project_root / "models" / "indic-parler-tts")
        _parler_tts.synthesize(text, output_path, language=ASRRouter.language_code(language))


def _raise_asr_error(code: str, message: str, status_code: int = 503) -> None:
    raise HTTPException(status_code=status_code, detail={"error": code, "message": message})


async def _run_asr(audio: UploadFile, session_id: str, language: str) -> str:
    if audio is None:
        _raise_asr_error("empty_audio", "No audio file was provided.", 400)

    raw_audio = await audio.read()
    if not raw_audio:
        _raise_asr_error("empty_audio", "No audio bytes were received. Please record or upload speech again.", 400)

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with _new_temporary_audio(suffix) as tmp:
        tmp.write(raw_audio)
        tmp_path = tmp.name

    converted_path: Path | None = None
    try:
        project_root = Path(__file__).resolve().parents[3]
        asr_router = ASRRouter(project_root)
        language_code = ASRRouter.language_code(language)
        azure_requested = (
            asr_router.azure_speech.configured
            and language_code in asr_router.azure_speech.ASR_LOCALES
        )
        input_path = tmp_path
        if azure_requested or suffix.lower() not in {".wav", ".flac", ".mp3"}:
            converted_path = await asyncio.to_thread(_convert_audio_to_azure_wav, tmp_path)
            input_path = converted_path

        if azure_requested:
            try:
                result = await asyncio.to_thread(asr_router.transcribe, input_path, language_code)
            except Exception as exc:  # pragma: no cover - surfaced to API layer
                _raise_asr_error(
                    "azure_asr_unavailable",
                    f"Azure ASR is unavailable or did not accept the audio. Details: {exc}",
                    502,
                )
        else:
            def transcribe_local() -> dict:
                with _speech_model_lock:
                    if _parler_tts is not None:
                        _parler_tts.unload()
                    try:
                        return asr_router.transcribe(input_path, language)
                    finally:
                        for engine in (asr_router.english_asr, asr_router.indic_asr):
                            unload = getattr(engine, "unload", None)
                            if callable(unload):
                                unload()

            try:
                result = await asyncio.to_thread(transcribe_local)
            except Exception as exc:
                _raise_asr_error("asr_unavailable", f"Speech recognition is unavailable. Details: {exc}", 503)

        transcript = str(result.get("text", "")).strip()
        if not transcript:
            _raise_asr_error(
                "empty_transcript",
                "No speech was detected in the audio. Please speak clearly or upload a cleaner recording.",
                422,
            )
        return transcript
    except HTTPException:
        raise
    except ValueError as exc:
        _raise_asr_error(
            "unsupported_audio_format",
            f"Unsupported audio format: {exc}",
            415,
        )
    except Exception as exc:
        _raise_asr_error("asr_unavailable", f"Speech recognition failed: {exc}", 503)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
            if converted_path:
                converted_path.unlink(missing_ok=True)
        except Exception:
            pass


def _convert_audio_to_azure_wav(audio_path: str | Path) -> Path:
    import av
    import numpy as np
    import soundfile as sf

    try:
        chunks = []
        with av.open(str(audio_path)) as container:
            stream = next((stream for stream in container.streams if stream.type == "audio"), None)
            if stream is None:
                raise ValueError("The uploaded file does not contain an audio stream.")
            resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in container.decode(stream):
                for converted_frame in resampler.resample(frame):
                    chunks.append(converted_frame.to_ndarray().reshape(-1))
    except (av.AVError, ValueError, OSError) as exc:
        raise ValueError(f"Unsupported audio format or unreadable file: {exc}") from exc

    if not chunks:
        raise ValueError("The uploaded audio contains no decodable samples.")
    with _new_temporary_audio(".wav") as converted:
        converted_path = Path(converted.name)
    sf.write(str(converted_path), np.concatenate(chunks), 16000, subtype="PCM_16")
    return converted_path
