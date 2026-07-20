import apiClient from './client';
import type { LoginRequest, LoginResponse, RegisterRequest, ChangePasswordRequest } from './types';

export const authAPI = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post('/auth/login', data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<void> => {
    await apiClient.post('/auth/register', data);
  },

  changePassword: async (data: ChangePasswordRequest, token: string): Promise<void> => {
    await apiClient.put('/auth/password', data, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  getMe: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },
};
