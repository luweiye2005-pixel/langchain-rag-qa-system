"""
DashScope 语音识别 (ASR) 与语音合成 (TTS)
移植自同级「语音问答」项目的核心逻辑。
"""
from http import HTTPStatus
from pathlib import Path

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback
from dashscope.audio.tts_v2 import AudioFormat, SpeechSynthesizer

from app.config import settings

# CosyVoice-v3-flash 官方系统音色
TTS_VOICES = [
    {"id": "longxiaochun_v3", "name": "龙小淳", "gender": "女", "desc": "知性积极"},
    {"id": "longanwen_v3", "name": "龙安温", "gender": "女", "desc": "优雅知性"},
    {"id": "longanrou_v3", "name": "龙安柔", "gender": "女", "desc": "温柔闺蜜"},
    {"id": "longanhuan", "name": "龙安欢", "gender": "女", "desc": "欢脱元气"},
    {"id": "longyingtao_v3", "name": "龙应桃", "gender": "女", "desc": "温柔淡定"},
    {"id": "longanyang", "name": "龙安洋", "gender": "男", "desc": "阳光大男孩"},
    {"id": "longanyun_v3", "name": "龙安昀", "gender": "男", "desc": "居家暖男"},
    {"id": "longanlang_v3", "name": "龙安朗", "gender": "男", "desc": "清爽利落"},
    {"id": "longshu_v3", "name": "龙书", "gender": "男", "desc": "沉稳青年"},
    {"id": "longfei_v3", "name": "龙飞", "gender": "男", "desc": "热血磁性"},
]
_TTS_VOICE_IDS = {v["id"] for v in TTS_VOICES}

ALLOWED_AUDIO_SUFFIXES = {".webm", ".wav", ".mp3", ".ogg", ".m4a", ".mp4", ".aac", ".opus"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_TTS_CHARS = 500


def _ensure_dashscope_api_key() -> None:
    if not settings.OPENAI_API_KEY:
        raise ValueError("缺少 OPENAI_API_KEY，无法调用 DashScope 语音服务")
    dashscope.api_key = settings.OPENAI_API_KEY


def resolve_voice(voice: str | None = None) -> str:
    """仅允许白名单音色，非法值回退到默认。"""
    if voice in _TTS_VOICE_IDS:
        return voice  # type: ignore[return-value]
    default = settings.TTS_VOICE
    return default if default in _TTS_VOICE_IDS else TTS_VOICES[0]["id"]


def _audio_format_from_suffix(suffix: str) -> str:
    """将文件后缀映射为 Recognition 支持的 format。"""
    mapping = {
        ".wav": "wav",
        ".mp3": "mp3",
        ".ogg": "opus",
        ".opus": "opus",
        ".aac": "aac",
        ".m4a": "aac",
        ".mp4": "aac",
        ".webm": "opus",
        ".pcm": "pcm",
    }
    fmt = mapping.get(suffix.lower())
    if not fmt:
        raise ValueError(f"不支持的音频格式: {suffix}")
    return fmt


def recognize_audio(file_path: str, suffix: str, sample_rate: int = 16000) -> str:
    """本地文件语音识别（paraformer-realtime）。"""
    _ensure_dashscope_api_key()
    fmt = _audio_format_from_suffix(suffix)
    recognition = Recognition(
        model="paraformer-realtime-v2",
        format=fmt,
        sample_rate=sample_rate,
        language_hints=["zh", "en"],
        callback=RecognitionCallback(),
    )
    result = recognition.call(file_path)
    if result.status_code != HTTPStatus.OK:
        raise RuntimeError(result.message or "语音识别失败")

    sentences = result.get_sentence()
    if not sentences:
        return ""
    if isinstance(sentences, dict):
        sentences = [sentences]
    return "".join(s.get("text", "") for s in sentences if isinstance(s, dict))


def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    """调用 CosyVoice 合成 WAV 音频。"""
    _ensure_dashscope_api_key()
    resolved = resolve_voice(voice)
    synthesizer = SpeechSynthesizer(
        model=settings.TTS_MODEL,
        voice=resolved,
        format=AudioFormat.WAV_16000HZ_MONO_16BIT,
    )
    audio = synthesizer.call(text)
    if not audio:
        raise RuntimeError("语音合成失败：未返回音频数据")
    return audio


def validate_audio_suffix(filename: str | None) -> str:
    """校验并返回小写后缀。"""
    suffix = Path(filename or "audio.wav").suffix.lower() or ".wav"
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        raise ValueError(
            f"不支持的音频格式: {suffix}，允许: {', '.join(sorted(ALLOWED_AUDIO_SUFFIXES))}"
        )
    return suffix
