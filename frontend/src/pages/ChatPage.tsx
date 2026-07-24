import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import { Input, Button, Empty, Spin, Typography, Space, Switch, Select, message, Tooltip } from 'antd';
import { SendOutlined, AudioOutlined, LoadingOutlined } from '@ant-design/icons';
import { streamChat } from '../api/chat';
import { conversationsAPI } from '../api/conversations';
import { voiceAPI, type TtsVoice } from '../api/voice';
import type { Message as MessageType, SSESourcesEvent } from '../api/types';
import MessageBubble from '../components/chat/MessageBubble';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';

const { Text } = Typography;

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const { refreshConversations } = useOutletContext<{ refreshConversations: () => Promise<void> }>();
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingSources, setStreamingSources] = useState<SSESourcesEvent['documents'] | null>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [voices, setVoices] = useState<TtsVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevConversationRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const inputValueRef = useRef(inputValue);
  inputValueRef.current = inputValue;

  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  const playTts = useCallback(async (text: string) => {
    if (!ttsEnabled || !text.trim()) return;
    try {
      stopPlayback();
      const blob = await voiceAPI.tts(text, selectedVoice || undefined);
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      await audio.play();
    } catch (err: any) {
      message.warning(err?.message || '语音播报失败');
    }
  }, [selectedVoice, stopPlayback, ttsEnabled]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  useEffect(() => {
    voiceAPI.getVoices()
      .then((data) => {
        setVoices(data.voices || []);
        setSelectedVoice(data.current || data.voices?.[0]?.id || '');
      })
      .catch(() => {
        // 语音服务不可用时静默；用户开启播报时再提示
      });
  }, []);

  // Clean up empty conversations when navigating away
  const cleanupEmptyConv = async (convId: string) => {
    try {
      const data = await conversationsAPI.getMessages(convId);
      if (data.total === 0) {
        await conversationsAPI.delete(convId);
        refreshConversations();
      }
    } catch {
      // Silently fail cleanup
    }
  };

  // Load messages when conversation changes, clean up old empty conversations
  useEffect(() => {
    stopPlayback();
    const prev = prevConversationRef.current;
    if (prev && prev !== conversationId) {
      cleanupEmptyConv(prev);
    }
    prevConversationRef.current = conversationId || null;

    if (conversationId) {
      loadMessages(conversationId);
    } else {
      setMessages([]);
    }
  }, [conversationId, stopPlayback]);

  useEffect(() => () => stopPlayback(), [stopPlayback]);

  const loadMessages = async (convId: string) => {
    setLoadingMessages(true);
    try {
      const data = await conversationsAPI.getMessages(convId);
      setMessages(data.messages);
    } catch {
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  const sendMessage = useCallback(async (rawText: string) => {
    const trimmed = rawText.trim();
    if (!trimmed || isStreaming) return;

    setInputValue('');
    setIsStreaming(true);
    setStreamingContent('');
    setStreamingSources(null);
    stopPlayback();

    const userMsg: MessageType = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId || '',
      role: 'user',
      content: trimmed,
      sources: null,
      token_count: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      let fullContent = '';
      let receivedSources: SSESourcesEvent['documents'] | null = null;
      for await (const event of streamChat(conversationId || null, trimmed)) {
        switch (event.type) {
          case 'token':
            fullContent += event.content;
            setStreamingContent(fullContent);
            break;
          case 'sources':
            receivedSources = event.documents;
            setStreamingSources(event.documents);
            break;
          case 'done':
            const newConvId = event.conversation_id;
            const activeConvId = newConvId || conversationId || '';

            const assistantMsg: MessageType = {
              id: `msg-${Date.now()}`,
              conversation_id: activeConvId,
              role: 'assistant',
              content: fullContent,
              sources: receivedSources,
              token_count: fullContent.length,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingContent('');
            setStreamingSources(null);

            if (newConvId) {
              navigate(`/chat/${newConvId}`, { replace: true });
              refreshConversations();
            }
            void playTts(fullContent);
            break;
          case 'error':
            throw new Error(event.message);
        }
      }
    } catch (err: any) {
      const errMsg: MessageType = {
        id: `err-${Date.now()}`,
        conversation_id: conversationId || '',
        role: 'assistant',
        content: `❌ 回答出错：${err.message || '未知错误'}`,
        sources: null,
        token_count: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsStreaming(false);
    }
  }, [conversationId, isStreaming, navigate, playTts, refreshConversations, stopPlayback]);

  const handleSend = useCallback(() => {
    void sendMessage(inputValueRef.current);
  }, [sendMessage]);

  const recorder = useVoiceRecorder({
    disabled: isStreaming,
    onText: (text) => {
      setInputValue(text);
      void sendMessage(text);
    },
    onError: (msg) => message.error(msg),
  });

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const femaleVoices = voices.filter((v) => v.gender === '女');
  const maleVoices = voices.filter((v) => v.gender === '男');

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Messages Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
        {loadingMessages ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin />
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Empty description="发送消息或点击麦克风开始对话" />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {isStreaming && streamingContent && (
              <MessageBubble
                message={{
                  id: 'streaming',
                  conversation_id: conversationId || '',
                  role: 'assistant',
                  content: streamingContent,
                  sources: streamingSources,
                  token_count: null,
                  created_at: null,
                }}
                isStreaming
              />
            )}

            {isStreaming && !streamingContent && (
              <div style={{ textAlign: 'center', padding: 16 }}>
                <Space>
                  <Spin size="small" />
                  <Text type="secondary">思考中...</Text>
                </Space>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div style={{
        borderTop: '1px solid #f0f0f0',
        padding: '12px 24px 16px',
        background: '#fff',
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto 8px', display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <Space size="small">
            <Text type="secondary">语音播报</Text>
            <Switch checked={ttsEnabled} onChange={setTtsEnabled} size="small" />
          </Space>
          <Select
            size="small"
            value={selectedVoice || undefined}
            onChange={setSelectedVoice}
            disabled={!ttsEnabled || voices.length === 0}
            placeholder="选择音色"
            style={{ minWidth: 180 }}
            options={[
              ...(femaleVoices.length
                ? [{ label: '女声', options: femaleVoices.map((v) => ({ value: v.id, label: `${v.name} · ${v.desc}` })) }]
                : []),
              ...(maleVoices.length
                ? [{ label: '男声', options: maleVoices.map((v) => ({ value: v.id, label: `${v.name} · ${v.desc}` })) }]
                : []),
            ]}
          />
        </div>
        <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', gap: 12, alignItems: 'flex-end' }}>
          <Input.TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={
              recorder.isRecording
                ? '正在录音，再次点击麦克风停止...'
                : recorder.isTranscribing
                  ? '正在识别语音...'
                  : '输入你的问题，或点击麦克风语音输入... (Enter 发送)'
            }
            autoSize={{ minRows: 1, maxRows: 5 }}
            disabled={isStreaming || recorder.isTranscribing}
            style={{ flex: 1 }}
          />
          <Tooltip title={!recorder.supported ? '当前浏览器不支持录音' : recorder.isRecording ? '停止录音' : '语音输入'}>
            <Button
              icon={recorder.isTranscribing ? <LoadingOutlined /> : <AudioOutlined />}
              onClick={() => void recorder.toggle()}
              disabled={!recorder.supported || isStreaming || recorder.isTranscribing}
              danger={recorder.isRecording}
              type={recorder.isRecording ? 'primary' : 'default'}
            />
          </Tooltip>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isStreaming}
            disabled={!inputValue.trim() || isStreaming || recorder.isRecording || recorder.isTranscribing}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
}
