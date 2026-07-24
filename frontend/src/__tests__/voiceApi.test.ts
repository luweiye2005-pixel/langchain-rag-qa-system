import { beforeEach, describe, expect, it, vi } from 'vitest';
import { voiceAPI } from '../api/voice';

vi.mock('../api/client', () => {
  const apiClient = {
    get: vi.fn(),
    post: vi.fn(),
  };
  return {
    default: apiClient,
    API_BASE_URL: '/api/v1',
  };
});

vi.mock('../stores/authStore', () => ({
  useAuthStore: {
    getState: () => ({ accessToken: 'access-token' }),
  },
}));

import apiClient from '../api/client';

describe('voiceAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getVoices returns voices payload', async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: { voices: [{ id: 'v1', name: 'A', gender: '女', desc: 'x' }], current: 'v1' },
    });
    const data = await voiceAPI.getVoices();
    expect(data.current).toBe('v1');
    expect(apiClient.get).toHaveBeenCalledWith('/voice/voices');
  });

  it('asr posts multipart and returns text', async () => {
    (apiClient.post as any).mockResolvedValueOnce({ data: { text: '你好' } });
    const text = await voiceAPI.asr(new Blob(['RIFF'], { type: 'audio/wav' }));
    expect(text).toBe('你好');
    expect(apiClient.post).toHaveBeenCalled();
  });

  it('tts returns audio blob', async () => {
    const blob = new Blob(['WAV'], { type: 'audio/wav' });
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      blob: async () => blob,
    }) as any;

    const result = await voiceAPI.tts('你好', 'longxiaochun_v3');
    expect(result).toBe(blob);
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/voice/tts',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('tts throws on http error', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: '合成失败' }),
    }) as any;

    await expect(voiceAPI.tts('你好')).rejects.toThrow('合成失败');
  });
});
