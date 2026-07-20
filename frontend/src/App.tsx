import { useEffect } from 'react';
import { useRoutes, useNavigate } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from './stores/authStore';
import { routes } from './router';

function App() {
  const { isAuthenticated, isAdmin, isRestoring, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, []);

  const element = useRoutes(routes(isAuthenticated, isAdmin, isRestoring));

  if (isRestoring) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f5f5f5' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return element;
}

export default App;
