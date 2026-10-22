"""
Transcription router — converts uploaded WAV audio to text using
Google Speech Recognition (via the SpeechRecognition library).
Audio is processed on the backend so the browser does NOT need
a direct connection to Google speech services.
"""

import io
import logging
import speech_recognition as sr
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["Transcription"])


@router.post("", response_model=dict)
@router.post("/", response_model=dict)
async def transcribe(file: UploadFile = File(...)):
    """
    Accept an audio WAV blob from the frontend and return
    the recognised text as JSON: {"text": "..."}.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received")

    try:
        audio_file = io.BytesIO(audio_bytes)
        recogniser = sr.Recognizer()

        with sr.AudioFile(audio_file) as source:
            audio_data = recogniser.record(source)

        text = recogniser.recognize_google(audio_data, language="en-IN")
        return JSONResponse(content={"text": text})

    except sr.UnknownValueError:
        # Audio was received but no clear speech was heard
        return JSONResponse(content={"text": ""})

    except sr.RequestError as exc:
        logger.exception("Google speech API request error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Speech recognition service is unavailable. Check internet connection.",
        )

    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {type(exc).__name__}: {exc}",
        )
