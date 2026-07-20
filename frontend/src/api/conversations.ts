import apiClient from './client';
import type { Conversation, Message } from './types';

export const conversationsAPI = {
  list: async (): Promise<{ conversations: Conversation[]; total: number }> => {
    const response = await apiClient.get('/conversations');
    return response.data;
  },

  create: async (title: string = '新对话'): Promise<Conversation> => {
    const response = await apiClient.post('/conversations', { title });
    return response.data;
  },

  get: async (id: string): Promise<Conversation> => {
    const response = await apiClient.get(`/conversations/${id}`);
    return response.data;
  },

  update: async (id: string, data: { title?: string; is_pinned?: boolean }): Promise<Conversation> => {
    const response = await apiClient.put(`/conversations/${id}`, data);
    return response.data;
  },

  pin: async (id: string, isPinned: boolean): Promise<Conversation> => {
    const response = await apiClient.put(`/conversations/${id}`, { is_pinned: isPinned });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/conversations/${id}`);
  },

  getMessages: async (id: string): Promise<{ messages: Message[]; total: number }> => {
    const response = await apiClient.get(`/conversations/${id}/messages`);
    return response.data;
  },
};
