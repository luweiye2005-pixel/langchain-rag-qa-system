"""
语音 ASR / TTS API
"""
import asyncio
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.rag.voice import (
    MAX_AUDIO_BYTES,
    MAX_TTS_CHARS,
    TTS_VOICES,
    recognize_audio,
    resolve_voice,
    synthesize_speech,
    validate_audio_suffix,
)

router = APIRouter()


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, description="待合成文本")
    voice: str | None = Field(None, description="音色 ID")


@router.get("/voices")
async def list_voices(current_user: User = Depends(get_current_user)):
    """返回可用 TTS 音色列表。"""
    return {"voices": TTS_VOICES, "current": resolve_voice()}


@router.post("/asr")
async def asr(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """语音识别：接收音频文件，返回识别文本。"""
    try:
        suffix = validate_audio_suffix(audio.filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="音频文件为空")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="音频文件过大")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        text = await asyncio.to_thread(recognize_audio, tmp_path, suffix)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语音识别失败: {e}",
        )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@router.post("/tts")
async def tts(
    request: TtsRequest,
    current_user: User = Depends(get_current_user),
):
    """语音合成：返回 WAV 音频。"""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文本不能为空")
    text = text[:MAX_TTS_CHARS]
    voice = resolve_voice(request.voice)

    try:
        audio_bytes = await asyncio.to_thread(synthesize_speech, text, voice)
        return Response(content=audio_bytes, media_type="audio/wav")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语音合成失败: {e}",
        )
