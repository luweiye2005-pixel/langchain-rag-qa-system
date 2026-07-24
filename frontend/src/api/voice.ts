import apiClient, { API_BASE_URL } from './client';
import { useAuthStore } from '../stores/authStore';

export interface TtsVoice {
  id: string;
  name: string;
  gender: string;
  desc: string;
}

export const voiceAPI = {
  async getVoices(): Promise<{ voices: TtsVoice[]; current: string }> {
    const response = await apiClient.get('/voice/voices');
    return response.data;
  },

  async asr(wavBlob: Blob): Promise<string> {
    const formData = new FormData();
    formData.append('audio', wavBlob, 'recording.wav');
    const response = await apiClient.post('/voice/asr', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return response.data.text || '';
  },

  async tts(text: string, voice?: string): Promise<Blob> {
    const token = useAuthStore.getState().accessToken;
    const response = await fetch(`${API_BASE_URL}/voice/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text, voice }),
    });
    if (!response.ok) {
      let detail = '语音合成失败';
      try {
        const data = await response.json();
        detail = data.detail || detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }
    return response.blob();
  },
};
