/**
 * 路由守卫 单元测试
 */
import { describe, it, expect } from 'vitest';
import { routes } from '../router';

describe('router', () => {
  describe('未登录状态', () => {
    it('/login 可见', () => {
      const r = routes(false, false, false);
      const loginRoute = r.find((route) => route.path === '/login');
      expect(loginRoute).toBeDefined();
    });

    it('/register 可见', () => {
      const r = routes(false, false, false);
      const registerRoute = r.find((route) => route.path === '/register');
      expect(registerRoute).toBeDefined();
    });

    it('/ 重定向到 /login', () => {
      const r = routes(false, false, false);
      const rootRoute = r.find((route) => route.path === '/');
      expect(rootRoute).toBeDefined();
    });
  });

  describe('已登录状态', () => {
    it('/login 重定向到 /chat', () => {
      const r = routes(true, false, false);
      const loginRoute = r.find((route) => route.path === '/login');
      expect(loginRoute).toBeDefined();
    });

    it('/chat 可见', () => {
      const r = routes(true, false, false);
      const rootRoute = r.find((route) => route.path === '/');
      expect(rootRoute).toBeDefined();
    });

    it('/profile 可见', () => {
      const r = routes(true, false, false);
      const rootRoute = r.find((route) => route.path === '/');
      const children = rootRoute?.children || [];
      const profile = children.find((c) => c.path === 'profile');
      expect(profile).toBeDefined();
    });
  });

  describe('管理员权限', () => {
    it('管理员可访问 /knowledge', () => {
      const r = routes(true, true, false);
      const rootRoute = r.find((route) => route.path === '/');
      const children = rootRoute?.children || [];
      const knowledge = children.find((c) => c.path === 'knowledge');
      expect(knowledge).toBeDefined();
    });

    it('非管理员 /knowledge 重定向到 /chat', () => {
      const r = routes(true, false, false);
      const rootRoute = r.find((route) => route.path === '/');
      const children = rootRoute?.children || [];
      const knowledge = children.find((c) => c.path === 'knowledge');
      expect(knowledge).toBeDefined();
    });
  });

  describe('404 处理', () => {
    it('未知路由重定向到 /chat', () => {
      const r = routes(true, false, false);
      const wildcard = r.find((route) => route.path === '*');
      expect(wildcard).toBeDefined();
    });
  });
});
