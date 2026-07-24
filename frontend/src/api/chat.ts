import { API_BASE_URL } from './client';
import { useAuthStore } from '../stores/authStore';
import type { ChatRequest, SSEEvent } from './types';

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

  const parseEvent = (rawEvent: string): SSEEvent | null => {
    const data = rawEvent
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).replace(/^ /, ''))
      .join('\n');

    if (!data) return null;

    try {
      return JSON.parse(data) as SSEEvent;
    } catch {
      return null;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: !done });
    }

    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() || '';
    for (const rawEvent of events) {
      const event = parseEvent(rawEvent);
      if (event) {
        yield event;
      }
    }

    if (done) break;
  }

  buffer += decoder.decode();
  const finalEvent = parseEvent(buffer);
  if (finalEvent) {
    yield finalEvent;
  }
}

export const chatAPI = {
  streamChat,
};
