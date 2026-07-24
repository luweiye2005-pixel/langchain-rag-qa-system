/**
 * API Types 单元测试
 */
import { describe, it, expect } from 'vitest';
import type {
  User, LoginRequest, LoginResponse, RegisterRequest,
  Conversation, Message, DocumentInfo,
  ChatRequest, SSEEvent, SourceDocument,
} from '../api/types';

describe('TypeScript Types', () => {
  describe('LoginRequest', () => {
    it('结构验证', () => {
      const req: LoginRequest = { username: 'admin', password: '123456' };
      expect(req.username).toBe('admin');
      expect(req.password).toBe('123456');
    });
  });

  describe('LoginResponse', () => {
    it('结构验证', () => {
      const resp: LoginResponse = {
        access_token: 'at',
        refresh_token: 'rt',
        token_type: 'Bearer',
        user: {
          id: '1', username: 'admin', email: 'a@b.com',
          is_admin: true, is_active: true, created_at: null,
        },
      };
      expect(resp.access_token).toBe('at');
      expect(resp.user.is_admin).toBe(true);
    });
  });

  describe('RegisterRequest', () => {
    it('结构验证', () => {
      const req: RegisterRequest = {
        username: 'newuser',
        email: 'new@test.com',
        password: 'pass123',
      };
      expect(req.email).toBe('new@test.com');
    });
  });

  describe('Conversation', () => {
    it('结构验证', () => {
      const conv: Conversation = {
        id: 'conv-1', user_id: 'user-1',
        title: '测试', is_archived: false,
        is_pinned: true, message_count: 5,
        created_at: null, updated_at: null,
      };
      expect(conv.is_pinned).toBe(true);
      expect(conv.message_count).toBe(5);
    });
  });

  describe('Message', () => {
    it('user 消息', () => {
      const msg: Message = {
        id: 'msg-1', conversation_id: 'conv-1',
        role: 'user', content: '你好',
        sources: null, token_count: null,
        created_at: '2024-01-01',
      };
      expect(msg.role).toBe('user');
      expect(msg.content).toBe('你好');
    });

    it('assistant 消息带来源', () => {
      const sources: SourceDocument[] = [{
        doc_id: 'doc-1', doc_name: 'test.pdf',
        chunk_id: '0', content_snippet: 'snippet',
        citation_index: 1,
        score: 0.95,
      }];
      const msg: Message = {
        id: 'msg-2', conversation_id: 'conv-1',
        role: 'assistant', content: '答案是...',
        sources, token_count: 150,
        created_at: '2024-01-01',
      };
      expect(msg.sources).toHaveLength(1);
      expect(msg.sources![0].score).toBe(0.95);
      expect(msg.sources![0].citation_index).toBe(1);
    });
  });

  describe('DocumentInfo', () => {
    it('结构验证', () => {
      const doc: DocumentInfo = {
        id: 'doc-1', filename: 'test.pdf',
        file_type: 'pdf', file_size: 2048,
        chunk_count: 10, status: 'completed',
        error_message: null, created_at: null,
      };
      expect(doc.status).toBe('completed');
      expect(doc.file_type).toBe('pdf');
    });
  });

  describe('ChatRequest', () => {
    it('新建会话请求', () => {
      const req: ChatRequest = {
        conversation_id: null,
        message: '你好',
      };
      expect(req.conversation_id).toBeNull();
    });

    it('已有会话请求', () => {
      const req: ChatRequest = {
        conversation_id: 'conv-123',
        message: '继续之前的话题',
      };
      expect(req.conversation_id).toBe('conv-123');
    });
  });

  describe('SSEEvent', () => {
    it('token 事件', () => {
      const event: SSEEvent = { type: 'token', content: '你好' };
      expect(event.type).toBe('token');
    });

    it('sources 事件', () => {
      const event: SSEEvent = { type: 'sources', documents: [] };
      expect(event.type).toBe('sources');
    });

    it('done 事件', () => {
      const event: SSEEvent = { type: 'done' };
      expect(event.type).toBe('done');
    });

    it('error 事件', () => {
      const event: SSEEvent = { type: 'error', message: '出错了' };
      expect(event.type).toBe('error');
      if (event.type === 'error') {
        expect(event.message).toBe('出错了');
      }
    });
  });
});
