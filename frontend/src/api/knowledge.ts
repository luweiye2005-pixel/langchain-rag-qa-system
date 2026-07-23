import apiClient from './client';
import type { DocumentContent, DocumentInfo } from './types';

export interface KnowledgeStats {
  total_documents: number;
  completed_documents: number;
  processing_documents: number;
  failed_documents: number;
  total_chunks: number;
  total_size_bytes: number;
  total_size_mb: number;
}

export const knowledgeAPI = {
  getDocuments: async (params?: {
    page?: number;
    size?: number;
    status?: string;
  }): Promise<{ documents: DocumentInfo[]; total: number }> => {
    const response = await apiClient.get('/knowledge/documents', { params });
    return response.data;
  },

  upload: async (file: File): Promise<DocumentInfo> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getDetail: async (id: string): Promise<DocumentInfo> => {
    const response = await apiClient.get(`/knowledge/documents/${id}`);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/knowledge/documents/${id}`);
  },

  reprocess: async (id: string): Promise<void> => {
    await apiClient.post(`/knowledge/documents/${id}/reprocess`);
  },

  getContent: async (id: string): Promise<DocumentContent> => {
    const response = await apiClient.get(`/knowledge/documents/${id}/content`);
    return response.data;
  },

  updateContent: async (id: string, content: string): Promise<{ message: string; status: string }> => {
    const response = await apiClient.put(`/knowledge/documents/${id}/content`, { content });
    return response.data;
  },

  getStats: async (): Promise<KnowledgeStats> => {
    const response = await apiClient.get('/knowledge/stats');
    return response.data;
  },
};
