import type { RouteObject } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ChatPage from './pages/ChatPage';
import KnowledgePage from './pages/KnowledgePage';
import ProfilePage from './pages/ProfilePage';
import { Navigate } from 'react-router-dom';

export const routes = (isAuthenticated: boolean, isAdmin: boolean, isRestoring: boolean): RouteObject[] => {
  // Don't show protected routes while restoring session
  const authed = isAuthenticated && !isRestoring;

  return [
    {
      path: '/login',
      element: authed ? <Navigate to="/chat" replace /> : <LoginPage />,
    },
    {
      path: '/register',
      element: authed ? <Navigate to="/chat" replace /> : <RegisterPage />,
    },
    {
      path: '/',
      element: authed ? <AppLayout /> : <Navigate to="/login" replace />,
      children: [
        {
          index: true,
          element: <Navigate to="/chat" replace />,
        },
        {
          path: 'chat',
          element: <ChatPage />,
        },
        {
          path: 'chat/:conversationId',
          element: <ChatPage />,
        },
        {
          path: 'profile',
          element: <ProfilePage />,
        },
        {
          path: 'knowledge',
          element: isAdmin ? <KnowledgePage /> : <Navigate to="/chat" replace />,
        },
      ],
    },
    {
      path: '*',
      element: <Navigate to="/chat" replace />,
    },
  ];
};
