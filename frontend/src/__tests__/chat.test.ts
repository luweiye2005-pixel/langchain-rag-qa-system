import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamChat } from '../api/chat';

describe('streamChat', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('解析被拆分且使用 CRLF 分隔的 SSE 事件', async () => {
    const encoder = new TextEncoder();
    const chunks = [
      encoder.encode('data: {"type":"token","content":"你'),
      encoder.encode('好"}\r\n\r\ndata: {"type":"done"}\r\n\r\n'),
    ];
    const reader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({ done: false, value: chunks[0] })
        .mockResolvedValueOnce({ done: false, value: chunks[1] })
        .mockResolvedValueOnce({ done: true, value: undefined }),
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => reader },
    }));

    const events = [];
    for await (const event of streamChat(null, '你好')) {
      events.push(event);
    }

    expect(events).toEqual([
      { type: 'token', content: '你好' },
      { type: 'done' },
    ]);
  });
});
