// ===== Auth =====
export interface User {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// ===== Conversation =====
export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  is_archived: boolean;
  is_pinned: boolean;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

// ===== Message =====
export interface SourceDocument {
  doc_id: string;
  doc_name: string;
  chunk_id: string;
  content_snippet: string;
  /** 与回答文本中 [n] 引用对应的编号。 */
  citation_index?: number;
  /** Chroma 余弦距离，数值越小表示越相关。 */
  score: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources: SourceDocument[] | null;
  token_count: number | null;
  created_at: string | null;
}

// ===== Document =====
export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  created_at: string | null;
}

// ===== Knowledge Content =====
export interface DocumentContent {
  document_id: string;
  filename: string;
  file_type: string;
  content: string;
  size: number;
}

// ===== Chat =====
export interface ChatRequest {
  conversation_id: string | null;
  message: string;
}

// ===== SSE Events =====
export interface SSETokenEvent {
  type: 'token';
  content: string;
}

export interface SSESourcesEvent {
  type: 'sources';
  documents: SourceDocument[];
}

export interface SSEDoneEvent {
  type: 'done';
  conversation_id?: string;
}

export interface SSEErrorEvent {
  type: 'error';
  message: string;
}

export type SSEEvent = SSETokenEvent | SSESourcesEvent | SSEDoneEvent | SSEErrorEvent;
