"""
语音 ASR / TTS 单元测试
"""
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from app.rag.voice import (
    MAX_TTS_CHARS,
    recognize_audio,
    resolve_voice,
    synthesize_speech,
    validate_audio_suffix,
)


class TestValidateAudioSuffix:
    def test_accepts_wav(self):
        assert validate_audio_suffix("a.wav") == ".wav"

    def test_rejects_unknown(self):
        with pytest.raises(ValueError, match="不支持的音频格式"):
            validate_audio_suffix("a.exe")


class TestResolveVoice:
    def test_whitelist(self):
        assert resolve_voice("longfei_v3") == "longfei_v3"

    def test_fallback_default(self):
        assert resolve_voice("not-a-voice") == "longxiaochun_v3"


class TestRecognizeAudio:
    @patch("app.rag.voice.Recognition")
    @patch("app.rag.voice.settings")
    def test_joins_sentences(self, mock_settings, mock_recognition_cls):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_recognition = MagicMock()
        mock_result = MagicMock()
        mock_result.status_code = HTTPStatus.OK
        mock_result.get_sentence.return_value = [
            {"text": "你好"},
            {"text": "世界"},
        ]
        mock_recognition.call.return_value = mock_result
        mock_recognition_cls.return_value = mock_recognition

        text = recognize_audio("/tmp/a.wav", ".wav")
        assert text == "你好世界"

    @patch("app.rag.voice.Recognition")
    @patch("app.rag.voice.settings")
    def test_raises_on_api_error(self, mock_settings, mock_recognition_cls):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_recognition = MagicMock()
        mock_result = MagicMock()
        mock_result.status_code = 500
        mock_result.message = "boom"
        mock_recognition.call.return_value = mock_result
        mock_recognition_cls.return_value = mock_recognition

        with pytest.raises(RuntimeError, match="boom"):
            recognize_audio("/tmp/a.wav", ".wav")


class TestSynthesizeSpeech:
    @patch("app.rag.voice.SpeechSynthesizer")
    @patch("app.rag.voice.settings")
    def test_returns_bytes(self, mock_settings, mock_synth_cls):
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.TTS_MODEL = "cosyvoice-v3-flash"
        mock_settings.TTS_VOICE = "longxiaochun_v3"
        mock_synth = MagicMock()
        mock_synth.call.return_value = b"RIFF...."
        mock_synth_cls.return_value = mock_synth

        audio = synthesize_speech("你好", "longxiaochun_v3")
        assert audio == b"RIFF...."
        mock_synth.call.assert_called_once_with("你好")

    def test_max_tts_chars_constant(self):
        assert MAX_TTS_CHARS == 500
