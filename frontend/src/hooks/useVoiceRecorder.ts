import { useCallback, useRef, useState } from 'react';
import { blobToWav16k, pickRecorderMimeType } from '../utils/audio';
import { voiceAPI } from '../api/voice';

export type VoiceRecorderStatus = 'idle' | 'recording' | 'transcribing';

interface UseVoiceRecorderOptions {
  onText: (text: string) => void;
  onError?: (message: string) => void;
  disabled?: boolean;
}

export function useVoiceRecorder({ onText, onError, disabled }: UseVoiceRecorderOptions) {
  const [status, setStatus] = useState<VoiceRecorderStatus>('idle');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined';

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  };

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
  }, []);

  const startRecording = useCallback(async () => {
    if (!supported || disabled || status !== 'idle') return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = pickRecorderMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stopTracks();
        setStatus('transcribing');
        try {
          if (chunksRef.current.length === 0) {
            setStatus('idle');
            return;
          }
          const blobType = mimeType || 'audio/webm';
          const audioBlob = new Blob(chunksRef.current, { type: blobType });
          const wavBlob = await blobToWav16k(audioBlob);
          const text = await voiceAPI.asr(wavBlob);
          if (!text.trim()) {
            onError?.('未识别到有效语音，请重试');
          } else {
            onText(text.trim());
          }
        } catch (err: any) {
          onError?.(err?.response?.data?.detail || err?.message || '语音识别失败');
        } finally {
          setStatus('idle');
          mediaRecorderRef.current = null;
        }
      };

      recorder.start();
      setStatus('recording');
    } catch (err: any) {
      stopTracks();
      setStatus('idle');
      if (err?.name === 'NotAllowedError') {
        onError?.('请允许麦克风权限后重试');
      } else {
        onError?.(err?.message || '无法启动录音');
      }
    }
  }, [disabled, onError, onText, status, supported]);

  const toggle = useCallback(async () => {
    if (status === 'recording') {
      stopRecording();
      return;
    }
    await startRecording();
  }, [startRecording, status, stopRecording]);

  return {
    supported,
    status,
    isRecording: status === 'recording',
    isTranscribing: status === 'transcribing',
    toggle,
    stopRecording,
  };
}
