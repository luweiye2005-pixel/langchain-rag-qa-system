import { Avatar, Typography, Card, Collapse, Tag, Space } from 'antd';
import { UserOutlined, RobotOutlined, FileTextOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { Message, SourceDocument } from '../../api/types';

const { Text, Paragraph } = Typography;

interface Props {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user';

  return (
    <div style={{
      display: 'flex',
      gap: 12,
      marginBottom: 20,
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      maxWidth: '85%',
      marginLeft: isUser ? 'auto' : 0,
      marginRight: isUser ? 0 : 'auto',
    }}>
      {!isUser && (
        <Avatar
          icon={<RobotOutlined />}
          style={{ backgroundColor: '#1677ff', flexShrink: 0 }}
        />
      )}

      <div style={{ flex: 1, minWidth: 0 }}>
        <Card
          size="small"
          style={{
            background: isUser ? '#e6f4ff' : '#ffffff',
            borderRadius: 12,
            border: isUser ? '1px solid #91caff' : '1px solid #f0f0f0',
          }}
          bodyStyle={{ padding: '12px 16px' }}
        >
          {/* Message Content */}
          <div className="message-content" style={{ lineHeight: 1.8 }}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {isStreaming && (
              <span className="cursor-blink" style={{
                display: 'inline-block',
                width: 2,
                height: 18,
                backgroundColor: '#1677ff',
                marginLeft: 2,
                verticalAlign: 'text-bottom',
              }} />
            )}
          </div>

          {/* Source Citations */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <Collapse
                ghost
                size="small"
                items={[{
                  key: 'sources',
                  label: (
                    <Space>
                      <FileTextOutlined />
                      <Text type="secondary">
                        参考来源 ({message.sources.length} 条)
                      </Text>
                    </Space>
                  ),
                  children: (
                    <div>
                      {message.sources.map((source: SourceDocument, idx: number) => {
                        const citationIndex = source.citation_index ?? idx + 1;
                        return (
                          <div key={`${source.doc_id}-${source.chunk_id}-${citationIndex}`} style={{
                            marginBottom: 8,
                            padding: '8px 12px',
                            background: '#fafafa',
                            borderRadius: 8,
                            borderLeft: '3px solid #1677ff',
                          }}>
                            <div style={{ marginBottom: 4 }}>
                              <Tag color="blue">[{citationIndex}]</Tag>
                              <Text strong style={{ fontSize: 13 }}>
                                {source.doc_name}
                              </Text>
                              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                距离: {source.score.toFixed(4)}
                              </Text>
                            </div>
                            <Paragraph
                              ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                              style={{ marginBottom: 0, fontSize: 13, color: '#666' }}
                            >
                              {source.content_snippet}
                            </Paragraph>
                          </div>
                        );
                      })}
                    </div>
                  ),
                }]}
              />
            </div>
          )}
        </Card>

        {/* Timestamp */}
        <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
          {message.created_at
            ? new Date(message.created_at).toLocaleTimeString('zh-CN')
            : ''}
        </Text>
      </div>

      {isUser && (
        <Avatar
          icon={<UserOutlined />}
          style={{ backgroundColor: '#52c41a', flexShrink: 0 }}
        />
      )}
    </div>
  );
}
