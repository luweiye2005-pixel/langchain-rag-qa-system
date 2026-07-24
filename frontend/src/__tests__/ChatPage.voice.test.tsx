import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';

const streamChatMock = vi.fn();
const getVoicesMock = vi.fn();
const ttsMock = vi.fn();
const toggleMock = vi.fn();

vi.mock('../api/chat', () => ({
  streamChat: (...args: unknown[]) => streamChatMock(...args),
}));

vi.mock('../api/conversations', () => ({
  conversationsAPI: {
    getMessages: vi.fn().mockResolvedValue({ messages: [], total: 0 }),
    delete: vi.fn(),
  },
}));

vi.mock('../api/voice', () => ({
  voiceAPI: {
    getVoices: (...args: unknown[]) => getVoicesMock(...args),
    tts: (...args: unknown[]) => ttsMock(...args),
    asr: vi.fn(),
  },
}));

vi.mock('../hooks/useVoiceRecorder', () => ({
  useVoiceRecorder: () => ({
    supported: true,
    status: 'idle',
    isRecording: false,
    isTranscribing: false,
    toggle: toggleMock,
    stopRecording: vi.fn(),
  }),
}));

vi.mock('../components/chat/MessageBubble', () => ({
  default: ({ message }: { message: { content: string } }) => (
    <div data-testid="bubble">{message.content}</div>
  ),
}));

import ChatPage from '../pages/ChatPage';

function Layout() {
  return <Outlet context={{ refreshConversations: vi.fn().mockResolvedValue(undefined) }} />;
}

function renderWithOutlet() {
  return render(
    <MemoryRouter initialEntries={['/chat']}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/chat" element={<ChatPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('ChatPage voice controls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    getVoicesMock.mockResolvedValue({
      voices: [
        { id: 'longxiaochun_v3', name: '龙小淳', gender: '女', desc: '知性积极' },
        { id: 'longfei_v3', name: '龙飞', gender: '男', desc: '热血磁性' },
      ],
      current: 'longxiaochun_v3',
    });
    streamChatMock.mockImplementation(async function* () {
      yield { type: 'token', content: '回答内容' };
      yield { type: 'done' };
    });
    ttsMock.mockResolvedValue(new Blob(['WAV'], { type: 'audio/wav' }));
    (globalThis as any).Audio = class {
      play = vi.fn().mockResolvedValue(undefined);
      pause = vi.fn();
    };
    URL.createObjectURL = vi.fn(() => 'blob:mock') as any;
    URL.revokeObjectURL = vi.fn() as any;
  });

  it('renders mic button and tts switch', async () => {
    renderWithOutlet();
    expect(await screen.findByText('语音播报')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /发送/ })).toBeInTheDocument();
    expect(screen.getAllByRole('button').length).toBeGreaterThanOrEqual(2);
  });

  it('sends text message and shows assistant reply', async () => {
    const user = userEvent.setup();
    renderWithOutlet();

    const textarea = await screen.findByPlaceholderText(/输入你的问题/);
    await user.type(textarea, '你好');
    await user.click(screen.getByRole('button', { name: /发送/ }));

    await waitFor(() => {
      expect(streamChatMock).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('回答内容')).toBeInTheDocument();
    });
  });

  it('plays tts after reply when switch enabled', async () => {
    const user = userEvent.setup();
    renderWithOutlet();

    const switchEl = await screen.findByRole('switch');
    await user.click(switchEl);

    const textarea = screen.getByPlaceholderText(/输入你的问题/);
    await user.type(textarea, '播报测试');
    await user.click(screen.getByRole('button', { name: /发送/ }));

    await waitFor(() => {
      expect(ttsMock).toHaveBeenCalled();
    });
    expect(ttsMock.mock.calls[0][0]).toContain('回答内容');
  });

  it('mic button triggers recorder toggle', async () => {
    const user = userEvent.setup();
    renderWithOutlet();
    await screen.findByText('语音播报');
    const buttons = screen.getAllByRole('button');
    const send = screen.getByRole('button', { name: /发送/ });
    const mic = buttons.find((b) => b !== send);
    expect(mic).toBeTruthy();
    await user.click(mic!);
    expect(toggleMock).toHaveBeenCalled();
  });
});
