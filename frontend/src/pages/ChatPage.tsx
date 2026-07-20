import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import { Input, Button, Empty, Spin, Typography, Space } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { streamChat } from '../api/chat';
import { conversationsAPI } from '../api/conversations';
import type { Message as MessageType, SSESourcesEvent } from '../api/types';
import MessageBubble from '../components/chat/MessageBubble';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevConversationRef = useRef<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // Clean up empty conversations when navigating away
  const cleanupEmptyConv = async (convId: string) => {
    try {
      // Check if old conversation is empty
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
  }, [conversationId]);


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

  const handleSend = useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isStreaming) return;

    setInputValue('');
    setIsStreaming(true);
    setStreamingContent('');
    setStreamingSources(null);

    // Add user message optimistically
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
      for await (const event of streamChat(conversationId || null, trimmed)) {
        switch (event.type) {
          case 'token':
            fullContent += event.content;
            setStreamingContent(fullContent);
            break;
          case 'sources':
            setStreamingSources(event.documents);
            break;
          case 'done':
            const newConvId = (event as any).conversation_id as string | undefined;
            const activeConvId = newConvId || conversationId || '';

            // Add assistant message
            const assistantMsg: MessageType = {
              id: `msg-${Date.now()}`,
              conversation_id: activeConvId,
              role: 'assistant',
              content: fullContent,
              sources: streamingSources || null,
              token_count: fullContent.length,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingContent('');
            setStreamingSources(null);

            // If new conversation, navigate to its URL and refresh sidebar
            if (newConvId) {
              navigate(`/chat/${newConvId}`, { replace: true });
              refreshConversations();
            }
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
  }, [inputValue, isStreaming, conversationId, streamingSources]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

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
            <Empty description="发送消息开始对话" />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {/* Streaming message */}
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
        padding: '16px 24px',
        background: '#fff',
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', gap: 12 }}>
          <Input.TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入你的问题... (Enter 发送，Shift+Enter 换行)"
            autoSize={{ minRows: 1, maxRows: 5 }}
            disabled={isStreaming}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isStreaming}
            disabled={!inputValue.trim() || isStreaming}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
}
