import { useState, useEffect, useCallback } from 'react';
import { Layout, Menu, Button, Avatar, Dropdown, Typography, Space, message, Modal, Input } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  MessageOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
  DatabaseOutlined,
  PushpinOutlined,
  PushpinFilled,
  EditOutlined,
  DeleteOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { conversationsAPI } from '../../api/conversations';
import type { Conversation } from '../../api/types';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const { user, isAdmin, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // Rename state
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const fetchConversations = useCallback(async () => {
    try {
      const data = await conversationsAPI.list();
      setConversations(data.conversations);
    } catch {
      // Silently fail
    }
  }, []);

  // Refresh sidebar on mount and when route changes
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations, location.pathname]);

  const handleNewChat = async () => {
    try {
      const conv = await conversationsAPI.create('新对话');
      await fetchConversations();
      navigate(`/chat/${conv.id}`);
    } catch {
      message.error('创建对话失败');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    message.success('已退出登录');
  };

  const handleRename = async () => {
    if (!renameTarget || !renameValue.trim()) return;
    try {
      await conversationsAPI.update(renameTarget.id, { title: renameValue.trim() });
      message.success('已改名');
      setRenameModalOpen(false);
      fetchConversations();
    } catch {
      message.error('改名失败');
    }
  };

  const openRenameModal = (conv: Conversation) => {
    setRenameTarget(conv);
    setRenameValue(conv.title);
    setRenameModalOpen(true);
  };

  const handlePin = async (conv: Conversation) => {
    try {
      const newPinned = !conv.is_pinned;
      await conversationsAPI.pin(conv.id, newPinned);
      message.success(newPinned ? '已置顶' : '已取消置顶');
      fetchConversations();
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = async (conv: Conversation) => {
    try {
      await conversationsAPI.delete(conv.id);
      message.success('已删除');
      // If currently viewing this conversation, go to home
      if (location.pathname.includes(conv.id)) {
        navigate('/chat');
      }
      fetchConversations();
    } catch {
      message.error('删除失败');
    }
  };

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人中心' },
    ...(isAdmin ? [{ key: 'knowledge', icon: <DatabaseOutlined />, label: '知识库管理' }] : []),
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const handleUserMenuClick = (info: { key: string }) => {
    switch (info.key) {
      case 'profile': navigate('/profile'); break;
      case 'knowledge': navigate('/knowledge'); break;
      case 'logout': handleLogout(); break;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={280}
        style={{ background: '#fff', borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}
      >
        {/* New Chat Button */}
        <div style={{ padding: '12px', borderBottom: '1px solid #f0f0f0' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleNewChat}
            block
          >
            {!collapsed && '新会话'}
          </Button>
        </div>

        {/* Conversation List */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {!collapsed && conversations.map((conv) => {
            const isActive = location.pathname === `/chat/${conv.id}`;
            return (
              <Dropdown
                key={conv.id}
                trigger={['contextMenu']}
                menu={{
                  items: [
                    {
                      key: 'rename',
                      icon: <EditOutlined />,
                      label: '重命名',
                      onClick: () => openRenameModal(conv),
                    },
                    {
                      key: 'pin',
                      icon: conv.is_pinned ? <PushpinOutlined /> : <PushpinFilled />,
                      label: conv.is_pinned ? '取消置顶' : '置顶',
                      onClick: () => handlePin(conv),
                    },
                    { type: 'divider' as const },
                    {
                      key: 'delete',
                      icon: <DeleteOutlined />,
                      label: '删除',
                      danger: true,
                      onClick: () => handleDelete(conv),
                    },
                  ],
                }}
              >
                <div
                  onClick={() => navigate(`/chat/${conv.id}`)}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    background: isActive ? '#e6f4ff' : 'transparent',
                    borderLeft: isActive ? '3px solid #1677ff' : '3px solid transparent',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    borderBottom: '1px solid #fafafa',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = isActive ? '#e6f4ff' : '#fafafa';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = isActive ? '#e6f4ff' : 'transparent';
                  }}
                >
                  <MessageOutlined style={{ fontSize: 14, color: '#999', flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 14,
                      fontWeight: isActive ? 600 : 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}>
                      {conv.is_pinned && (
                        <PushpinFilled style={{ color: '#1677ff', fontSize: 11, flexShrink: 0 }} />
                      )}
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{conv.title}</span>
                    </div>
                  </div>

                  {/* 3-dot menu button */}
                  <Dropdown
                    menu={{
                      items: [
                        {
                          key: 'rename',
                          icon: <EditOutlined />,
                          label: '重命名',
                          onClick: (e) => { e.domEvent.stopPropagation(); openRenameModal(conv); },
                        },
                        {
                          key: 'pin',
                          icon: conv.is_pinned ? <PushpinOutlined /> : <PushpinFilled />,
                          label: conv.is_pinned ? '取消置顶' : '置顶',
                          onClick: (e) => { e.domEvent.stopPropagation(); handlePin(conv); },
                        },
                        { type: 'divider' as const },
                        {
                          key: 'delete',
                          icon: <DeleteOutlined />,
                          label: '删除',
                          danger: true,
                          onClick: (e) => { e.domEvent.stopPropagation(); handleDelete(conv); },
                        },
                      ],
                    }}
                    placement="bottomRight"
                    trigger={['click']}
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<MoreOutlined />}
                      onClick={(e) => e.stopPropagation()}
                      style={{ flexShrink: 0, opacity: 0.5 }}
                    />
                  </Dropdown>
                </div>
              </Dropdown>
            );
          })}

          {conversations.length === 0 && !collapsed && (
            <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>
              <Text type="secondary">暂无会话</Text>
            </div>
          )}
        </div>

        {/* Collapsed: show simple icon list */}
        {collapsed && (
          <div style={{ flex: 1, overflow: 'auto', paddingTop: 8 }}>
            {conversations.map((conv) => {
              const isActive = location.pathname === `/chat/${conv.id}`;
              return (
                <div
                  key={conv.id}
                  onClick={() => navigate(`/chat/${conv.id}`)}
                  style={{
                    padding: '12px',
                    cursor: 'pointer',
                    textAlign: 'center',
                    background: isActive ? '#e6f4ff' : 'transparent',
                    borderLeft: isActive ? '3px solid #1677ff' : '3px solid transparent',
                  }}
                  title={conv.title}
                >
                  <MessageOutlined style={{ fontSize: 18, color: isActive ? '#1677ff' : '#999' }} />
                </div>
              );
            })}
          </div>
        )}
      </Sider>

      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
          height: 56,
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />

          <Space size="large">
            {isAdmin && (
              <Button
                type="text"
                icon={<DatabaseOutlined />}
                onClick={() => navigate('/knowledge')}
              >
                知识库管理
              </Button>
            )}
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} size="small" />
                <Text>{user?.username}</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ background: '#f5f5f5', height: 'calc(100vh - 56px)' }}>
          <Outlet context={{ refreshConversations: fetchConversations }} />
        </Content>
      </Layout>

      {/* Rename Modal */}
      <Modal
        title="重命名会话"
        open={renameModalOpen}
        onOk={handleRename}
        onCancel={() => setRenameModalOpen(false)}
        okText="确认"
        cancelText="取消"
      >
        <Input
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onPressEnter={handleRename}
          placeholder="输入新名称"
          maxLength={200}
          autoFocus
        />
      </Modal>
    </Layout>
  );
}
