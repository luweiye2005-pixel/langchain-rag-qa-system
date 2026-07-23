import { useState, useEffect, useCallback } from 'react';
import { Card, Table, Button, Upload, Tag, Popconfirm, Space, message, Statistic, Row, Col } from 'antd';
import { UploadOutlined, DeleteOutlined, ReloadOutlined, FileTextOutlined, InboxOutlined, EyeOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { knowledgeAPI, type KnowledgeStats } from '../api/knowledge';
import type { DocumentInfo } from '../api/types';
import DocumentContentModal from '../components/knowledge/DocumentContentModal';

const { Dragger } = Upload;

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [contentModalOpen, setContentModalOpen] = useState(false);
  const [contentModalDoc, setContentModalDoc] = useState<DocumentInfo | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [docsData, statsData] = await Promise.all([
        knowledgeAPI.getDocuments({ size: 100 }),
        knowledgeAPI.getStats(),
      ]);
      setDocuments(docsData.documents);
      setStats(statsData);
    } catch (err: any) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await knowledgeAPI.upload(file);
      message.success(`"${file.name}" 上传成功，正在处理中`);
      // Poll for updates
      setTimeout(fetchData, 2000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || '上传失败';
      message.error(detail);
    } finally {
      setUploading(false);
    }
    return false; // Prevent default upload behavior
  };

  const handleDelete = async (id: string) => {
    try {
      await knowledgeAPI.delete(id);
      message.success('文档已删除');
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  const handleReprocess = async (id: string) => {
    try {
      await knowledgeAPI.reprocess(id);
      message.success('已重新处理');
      fetchData();
    } catch {
      message.error('重新处理失败');
    }
  };

  const statusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待处理' },
      processing: { color: 'processing', text: '处理中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const { color, text } = map[status] || { color: 'default', text: status };
    return <Tag color={color}>{text}</Tag>;
  };

  const columns = [
    { title: '文件名', dataIndex: 'filename', key: 'filename', ellipsis: true },
    { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 80, render: (t: string) => t.toUpperCase() },
    {
      title: '大小', dataIndex: 'file_size', key: 'file_size', width: 100,
      render: (size: number) => {
        if (size > 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
        if (size > 1024) return `${(size / 1024).toFixed(1)} KB`;
        return `${size} B`;
      },
    },
    { title: '片段数', dataIndex: 'chunk_count', key: 'chunk_count', width: 80 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: statusTag },
    {
      title: '操作', key: 'actions', width: 240,
      render: (_: any, record: DocumentInfo) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => { setContentModalDoc(record); setContentModalOpen(true); }}
          >
            查看
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => handleReprocess(record.id)} disabled={record.status === 'processing'}>
            重处理
          </Button>
          <Popconfirm title="确认删除此文档？" onConfirm={() => handleDelete(record.id)} okText="确认" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <h2>知识库管理</h2>

      {/* Stats */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}><Card><Statistic title="文档总数" value={stats.total_documents} prefix={<FileTextOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="已完成" value={stats.completed_documents} valueStyle={{ color: '#52c41a' }} /></Card></Col>
          <Col span={6}><Card><Statistic title="处理中" value={stats.processing_documents} valueStyle={{ color: '#1677ff' }} /></Card></Col>
          <Col span={6}><Card><Statistic title="总片段数" value={stats.total_chunks} /></Card></Col>
        </Row>
      )}

      {/* Upload */}
      <Card style={{ marginBottom: 24 }}>
        <Dragger
          accept=".pdf,.txt,.csv,.md,.docx"
          showUploadList={false}
          beforeUpload={(file) => { handleUpload(file); return false; }}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
          <p className="ant-upload-hint">支持 PDF, TXT, CSV, Markdown, DOCX 格式，单个文件不超过 50MB</p>
        </Dragger>
      </Card>

      {/* Document Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      {/* Document Content Modal */}
      <DocumentContentModal
        document={contentModalDoc}
        open={contentModalOpen}
        onClose={() => { setContentModalOpen(false); setContentModalDoc(null); }}
        onSaved={fetchData}
      />
    </div>
  );
}
