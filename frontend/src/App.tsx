import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN_antd from 'antd/locale/zh_CN';
import enUS_antd from 'antd/locale/en_US';
import { useAppStore } from './store';
import { useSystemTheme } from './hooks/useSystemTheme';
import { getThemeConfig } from './themes';
import AppLayout from './components/Layout';
import Loading from './components/Common/Loading';

// Lazy load pages
const Login = React.lazy(() => import('./pages/Login'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const MarketData = React.lazy(() => import('./pages/MarketData'));
const Strategies = React.lazy(() => import('./pages/Strategies'));
const Backtest = React.lazy(() => import('./pages/Backtest'));
const Trading = React.lazy(() => import('./pages/Trading'));
const Portfolio = React.lazy(() => import('./pages/Portfolio'));
const Alerts = React.lazy(() => import('./pages/Alerts'));
const UserCenter = React.lazy(() => import('./pages/UserCenter'));

function AppContent() {
  const { themeMode, resolvedTheme, setResolvedTheme, language, isAuthenticated } = useAppStore();
  const systemTheme = useSystemTheme();

  // Resolve theme
  useEffect(() => {
    const newResolved = themeMode === 'auto' ? systemTheme : themeMode;
    setResolvedTheme(newResolved);
    // Add theme transition class
    document.body.classList.add('theme-transition');
    const timer = setTimeout(() => document.body.classList.remove('theme-transition'), 400);
    // Set data attribute for CSS
    document.documentElement.setAttribute('data-theme', newResolved);
    return () => clearTimeout(timer);
  }, [themeMode, systemTheme, setResolvedTheme]);

  const themeConfig = getThemeConfig(resolvedTheme);
  const antLocale = language === 'zh-CN' ? zhCN_antd : enUS_antd;

  return (
    <ConfigProvider theme={themeConfig} locale={antLocale}>
      <AntApp>
        <BrowserRouter>
          <React.Suspense fallback={<Loading fullPage />}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={isAuthenticated ? <AppLayout /> : <Navigate to="/login" />}>
                <Route index element={<Navigate to="/dashboard" />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="market" element={<MarketData />} />
                <Route path="strategies" element={<Strategies />} />
                <Route path="backtest" element={<Backtest />} />
                <Route path="trading" element={<Trading />} />
                <Route path="portfolio" element={<Portfolio />} />
                <Route path="alerts" element={<Alerts />} />
                <Route path="user-center" element={<UserCenter />} />
              </Route>
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </React.Suspense>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

export default function App() {
  return <AppContent />;
}
