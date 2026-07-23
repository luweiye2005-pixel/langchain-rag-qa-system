/**
 * Auth Store (Zustand) 单元测试
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useAuthStore } from '../stores/authStore';

// Mock auth API
vi.mock('../api/auth', () => ({
  authAPI: {
    login: vi.fn(),
    register: vi.fn(),
    changePassword: vi.fn(),
  },
}));

// Mock API client
vi.mock('../api/client', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('useAuthStore', () => {
  beforeEach(() => {
    // 重置 store 状态
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isAdmin: false,
      isRestoring: true,
    });
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // =========================================
  // 初始状态
  // =========================================
  describe('initial state', () => {
    it('初始状态 isAuthenticated 为 false', () => {
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isAdmin).toBe(false);
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
    });

    it('初始状态 isRestoring 为 true', () => {
      const state = useAuthStore.getState();
      expect(state.isRestoring).toBe(true);
    });
  });

  // =========================================
  // login
  // =========================================
  describe('login', () => {
    it('登录成功更新状态', async () => {
      const { authAPI } = await import('../api/auth');
      const mockResponse = {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        user: {
          id: 'user-1',
          username: 'admin',
          email: 'admin@test.com',
          is_admin: true,
          is_active: true,
          created_at: null,
        },
      };
      (authAPI.login as any).mockResolvedValueOnce(mockResponse);

      const store = useAuthStore.getState();
      await store.login('admin', '123456');

      const newState = useAuthStore.getState();
      expect(newState.isAuthenticated).toBe(true);
      expect(newState.isAdmin).toBe(true);
      expect(newState.accessToken).toBe('test-access-token');
      expect(newState.refreshToken).toBe('test-refresh-token');
      expect(newState.user?.username).toBe('admin');
    });

    it('登录成功存储 token 到 storage', async () => {
      const { authAPI } = await import('../api/auth');
      (authAPI.login as any).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        user: { id: '1', username: 'u', email: 'e', is_admin: false, is_active: true, created_at: null },
      });

      const store = useAuthStore.getState();
      await store.login('u', 'p');

      expect(sessionStorage.getItem('accessToken')).toBe('at');
      expect(localStorage.getItem('refreshToken')).toBe('rt');
      expect(localStorage.getItem('user')).toBeTruthy();
    });

    it('登录失败不更新状态', async () => {
      const { authAPI } = await import('../api/auth');
      (authAPI.login as any).mockRejectedValueOnce(new Error('Network error'));

      const store = useAuthStore.getState();
      try {
        await store.login('admin', 'wrong');
      } catch { /* expected */ }

      const newState = useAuthStore.getState();
      expect(newState.isAuthenticated).toBe(false);
      expect(newState.user).toBeNull();
    });
  });

  // =========================================
  // logout
  // =========================================
  describe('logout', () => {
    it('登出清除所有状态和存储', async () => {
      // 先模拟登录
      const { authAPI } = await import('../api/auth');
      (authAPI.login as any).mockResolvedValueOnce({
        access_token: 'at',
        refresh_token: 'rt',
        user: { id: '1', username: 'u', email: 'e', is_admin: true, is_active: true, created_at: null },
      });

      const store = useAuthStore.getState();
      await store.login('admin', 'p');

      // 确认登录成功
      expect(useAuthStore.getState().isAuthenticated).toBe(true);

      // 登出
      useAuthStore.getState().logout();

      const newState = useAuthStore.getState();
      expect(newState.isAuthenticated).toBe(false);
      expect(newState.isAdmin).toBe(false);
      expect(newState.user).toBeNull();
      expect(newState.accessToken).toBeNull();
      expect(newState.refreshToken).toBeNull();
      expect(sessionStorage.getItem('accessToken')).toBeNull();
      expect(localStorage.getItem('refreshToken')).toBeNull();
    });
  });

  // =========================================
  // register
  // =========================================
  describe('register', () => {
    it('注册成功不自动登录', async () => {
      const { authAPI } = await import('../api/auth');
      (authAPI.register as any).mockResolvedValueOnce({});

      const store = useAuthStore.getState();
      await store.register('newuser', 'new@test.com', 'pass');

      // 注册后不应改变认证状态
      const newState = useAuthStore.getState();
      expect(newState.isAuthenticated).toBe(false);
    });
  });
});
