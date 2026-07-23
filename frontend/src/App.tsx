import { useEffect } from 'react';
import { useRoutes, useNavigate } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from './stores/authStore';
import { routes } from './router';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  const { isAuthenticated, isAdmin, isRestoring, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const element = useRoutes(routes(isAuthenticated, isAdmin, isRestoring));

  if (isRestoring) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f5f5f5' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return <ErrorBoundary>{element}</ErrorBoundary>;
}

export default App;
