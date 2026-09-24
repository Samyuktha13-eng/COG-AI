"""
Voice API
=========
POST /api/voice/transcribe          — transcribe any audio (generic)
POST /api/voice/caregiver-prompt    — caregiver speaks → ASR → GroundingAgent resolve
                                      (same result as POST /api/grounding/resolve with text)
"""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..models.grounding import GroundingResult
from ..services.grounding import GroundingAgent
from voice.asr_router import ASRRouter
from voice.intent import IntentRouter

router = APIRouter(prefix="/api/voice", tags=["voice"])
_intent_router = IntentRouter()


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """Generic transcription endpoint — returns raw transcript."""
    transcript = await _run_asr(audio, "generic", language)
    return {"transcript": transcript, "language": language}


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

async def _run_asr(audio: UploadFile, session_id: str, language: str) -> str:
    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    converted_path: Path | None = None
    try:
        project_root = Path(__file__).resolve().parents[3]
        input_path = tmp_path
        if suffix.lower() not in {".wav", ".flac", ".mp3"}:
            import av
            import numpy as np
            import soundfile as sf

            chunks = []
            with av.open(str(tmp_path)) as container:
                stream = next(stream for stream in container.streams if stream.type == "audio")
                resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
                for frame in container.decode(stream):
                    for converted_frame in resampler.resample(frame):
                        chunks.append(converted_frame.to_ndarray().reshape(-1))
            if not chunks:
                raise ValueError("The uploaded audio contains no decodable samples.")
            with NamedTemporaryFile(suffix=".wav", delete=False) as converted:
                converted_path = Path(converted.name)
            sf.write(str(converted_path), np.concatenate(chunks), 16000, subtype="PCM_16")
            input_path = converted_path

        result = ASRRouter(project_root).transcribe(input_path, language)
        return str(result.get("text", "")).strip()
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "asr_unavailable", "message": str(exc)}) from exc
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
            if converted_path:
                converted_path.unlink(missing_ok=True)
        except Exception:
            pass
