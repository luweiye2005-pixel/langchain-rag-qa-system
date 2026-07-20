import apiClient from './client';
import { useAuthStore } from '../stores/authStore';
import type { ChatRequest, SSEEvent } from './types';

const API_BASE_URL = '/api/v1';

/**
 * SSE 流式聊天
 * 使用 ReadableStream 发送 POST 请求并接收 SSE 事件
 */
export async function* streamChat(
  conversationId: string | null,
  message: string,
): AsyncGenerator<SSEEvent> {
  const token = useAuthStore.getState().accessToken;

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
    } as ChatRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法读取响应流');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: SSEEvent = JSON.parse(line.slice(6));
          yield event;
        } catch {
          // Skip unparseable lines
        }
      }
    }
  }
}

export const chatAPI = {
  streamChat,
};
