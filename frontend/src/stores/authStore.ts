import { create } from 'zustand';
import { authAPI } from '../api/auth';
import apiClient from '../api/client';
import type { User } from '../api/types';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isRestoring: boolean;  // True while restoring session from storage
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  restoreSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isAdmin: false,
  isRestoring: true,

  login: async (username: string, password: string) => {
    const response = await authAPI.login({ username, password });
    const { access_token, refresh_token, user } = response;
    set({
      user,
      accessToken: access_token,
      refreshToken: refresh_token,
      isAuthenticated: true,
      isAdmin: user.is_admin,
    });
    localStorage.setItem('refreshToken', refresh_token);
    localStorage.setItem('user', JSON.stringify(user));
    sessionStorage.setItem('accessToken', access_token);
  },

  register: async (username: string, email: string, password: string) => {
    await authAPI.register({ username, email, password });
  },

  logout: () => {
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isAdmin: false,
    });
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    sessionStorage.removeItem('accessToken');
  },

  changePassword: async (oldPassword: string, newPassword: string) => {
    await authAPI.changePassword(
      { old_password: oldPassword, new_password: newPassword },
      get().accessToken!,
    );
  },

  restoreSession: async () => {
    const storedRefresh = localStorage.getItem('refreshToken');
    const storedUser = localStorage.getItem('user');
    const storedAccess = sessionStorage.getItem('accessToken');

    if (!storedRefresh) {
      set({ isRestoring: false });
      return;
    }

    try {
      // Try to get a fresh access token
      const response = await apiClient.post('/auth/refresh', {
        refresh_token: storedRefresh,
      });
      const { access_token: accessToken, refresh_token: refreshToken } = response.data;
      sessionStorage.setItem('accessToken', accessToken);
      localStorage.setItem('refreshToken', refreshToken);

      const user = storedUser ? JSON.parse(storedUser) : null;
      set({
        user,
        accessToken,
        refreshToken,
        isAuthenticated: true,
        isAdmin: user?.is_admin ?? false,
        isRestoring: false,
      });
    } catch {
      // Refresh failed - clear everything
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      sessionStorage.removeItem('accessToken');
      set({ isRestoring: false });
    }
  },
}));
