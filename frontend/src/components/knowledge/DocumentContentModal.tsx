import { useState, useEffect } from 'react';
import { Modal, Button, Input, Spin, Tag, message, Space, Typography } from 'antd';
import { EditOutlined, FileTextOutlined, EyeOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { knowledgeAPI } from '../../api/knowledge';
import type { DocumentInfo } from '../../api/types';

const { Text } = Typography;

interface Props {
  document: DocumentInfo | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const TEXT_TYPES = ['txt', 'md', 'csv'];

export default function DocumentContentModal({ document, open, onClose, onSaved }: Props) {
  const [content, setContent] = useState('');
  const [editedContent, setEditedContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (open && document && TEXT_TYPES.includes(document.file_type)) {
      setLoading(true);
      setEditing(false);
      knowledgeAPI.getContent(document.id)
        .then((data) => {
          setContent(data.content);
          setEditedContent(data.content);
        })
        .catch((err) => {
          const detail = err?.response?.data?.detail || '获取文档内容失败';
          message.error(detail);
        })
        .finally(() => setLoading(false));
    }
  }, [open, document?.id]);

  if (!document) return null;

  const isTextFile = TEXT_TYPES.includes(document.file_type);

  const handleSave = async () => {
    if (!document) return;
    if (editedContent === content) {
      message.info('内容未修改');
      return;
    }
    setSaving(true);
    try {
      await knowledgeAPI.updateContent(document.id, editedContent);
      message.success('内容已保存，文档正在重新处理中');
      setEditing(false);
      onSaved();
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || '保存失败';
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditedContent(content);
    setEditing(false);
  };

  const footer = [
    <Button key="close" onClick={onClose}>关闭</Button>,
  ];

  if (isTextFile && !editing) {
    footer.push(
      <Button key="edit" type="primary" icon={<EditOutlined />} onClick={() => setEditing(true)}>
        编辑
      </Button>,
    );
  }

  if (editing) {
    footer.push(
      <Button key="cancel-edit" onClick={handleCancelEdit}>取消编辑</Button>,
      <Button key="save" type="primary" loading={saving} onClick={handleSave}>
        保存并重新处理
      </Button>,
    );
  }

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          <span>{document.filename}</span>
          <Tag color="blue">{document.file_type.toUpperCase()}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {document.file_size > 1024
              ? `${(document.file_size / 1024).toFixed(1)} KB`
              : `${document.file_size} B`}
          </Text>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={900}
      footer={footer}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin tip="加载文档内容..." />
        </div>
      ) : !isTextFile ? (
        <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
          <FileTextOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <p>{document.file_type.toUpperCase()} 为二进制格式，不支持在线预览</p>
          <Text type="secondary">请下载文件后使用本地编辑器查看和编辑</Text>
        </div>
      ) : editing ? (
        <div>
          <Input.TextArea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            rows={22}
            style={{ fontFamily: 'Consolas, Monaco, "Courier New", monospace', fontSize: 13 }}
            placeholder="编辑文档内容..."
            autoFocus
          />
          <div style={{ marginTop: 8, textAlign: 'right' }}>
            <Text type="secondary">字符数: {editedContent.length}</Text>
          </div>
        </div>
      ) : (
        <div
          style={{
            maxHeight: '65vh',
            overflow: 'auto',
            padding: '16px 20px',
            background: '#fafafa',
            borderRadius: 8,
            border: '1px solid #f0f0f0',
          }}
        >
          {document.file_type === 'md' ? (
            <div className="message-content" style={{ lineHeight: 1.8 }}>
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          ) : (
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: 13,
              lineHeight: 1.8,
              margin: 0,
              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            }}>
              {content}
            </pre>
          )}
        </div>
      )}
    </Modal>
  );
}
