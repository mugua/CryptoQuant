import React from 'react';
import { Layout, Menu, Button, Badge, Avatar, Dropdown, Space } from 'antd';
import {
  DashboardOutlined,
  LineChartOutlined,
  RobotOutlined,
  HistoryOutlined,
  SwapOutlined,
  PieChartOutlined,
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ThunderboltOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../../store';
import { authApi } from '../../api/auth';
import ThemeSwitch from '../Common/ThemeSwitch';
import LanguageSwitch from '../Common/LanguageSwitch';

const { Sider, Header, Content } = Layout;

const SIDER_WIDTH = 220;
const SIDER_COLLAPSED_WIDTH = 64;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, labelKey: 'nav.dashboard' },
  { key: '/market', icon: <LineChartOutlined />, labelKey: 'nav.market' },
  { key: '/strategies', icon: <RobotOutlined />, labelKey: 'nav.strategies' },
  { key: '/backtest', icon: <HistoryOutlined />, labelKey: 'nav.backtest' },
  { key: '/trading', icon: <SwapOutlined />, labelKey: 'nav.trading' },
  { key: '/portfolio', icon: <PieChartOutlined />, labelKey: 'nav.portfolio' },
  { key: '/alerts', icon: <BellOutlined />, labelKey: 'nav.alerts' },
];

const AppLayout: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAppStore((s) => s.user);
  const sidebarCollapsed = useAppStore((s) => s.sidebarCollapsed);
  const setSidebarCollapsed = useAppStore((s) => s.setSidebarCollapsed);
  const unreadCount = useAppStore((s) => s.unreadCount);
  const logout = useAppStore((s) => s.logout);

  const selectedKey =
    menuItems.find((item) => location.pathname.startsWith(item.key))?.key ?? '/dashboard';

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // proceed with local logout regardless
    }
    logout();
    navigate('/login');
  };

  const userMenuItems = [
    {
      key: 'user-center',
      icon: <UserOutlined />,
      label: t('nav.userCenter'),
      onClick: () => navigate('/user-center'),
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('auth.logout'),
      danger: true,
      onClick: handleLogout,
    },
  ];

  const currentWidth = sidebarCollapsed ? SIDER_COLLAPSED_WIDTH : SIDER_WIDTH;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={SIDER_WIDTH}
        collapsedWidth={SIDER_COLLAPSED_WIDTH}
        collapsed={sidebarCollapsed}
        trigger={null}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          background: '#0d1117',
          zIndex: 100,
          overflow: 'auto',
        }}
      >
        <div className="sidebar-logo" onClick={() => navigate('/dashboard')}>
          <ThunderboltOutlined
            style={{
              fontSize: 24,
              background: 'linear-gradient(135deg, #42a5f5, #7c4dff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          />
          {!sidebarCollapsed && <span className="sidebar-logo-text">CryptoQuant</span>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
          style={{ background: 'transparent', borderInlineEnd: 'none' }}
          items={menuItems.map((item) => ({
            key: item.key,
            icon: item.icon,
            label: t(item.labelKey),
          }))}
        />
      </Sider>

      <Layout
        style={{
          marginLeft: currentWidth,
          transition: 'margin-left 0.2s ease',
        }}
      >
        <Header
          className="app-header"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 99,
            background: '#0d1117',
            height: 56,
            lineHeight: '56px',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <Button
            type="text"
            icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            style={{ fontSize: 16, color: 'rgba(255,255,255,0.85)' }}
          />
          <Space size={16} align="center">
            <ThemeSwitch />
            <LanguageSwitch />
            <Badge count={unreadCount} size="small" offset={[-4, 4]}>
              <Button
                type="text"
                icon={<BellOutlined />}
                onClick={() => navigate('/alerts')}
                style={{ color: 'rgba(255,255,255,0.85)' }}
              />
            </Badge>
            <Dropdown menu={{ items: userMenuItems }} trigger={['click']} placement="bottomRight">
              <Avatar
                size={32}
                src={user?.avatar_url}
                icon={!user?.avatar_url ? <UserOutlined /> : undefined}
                style={{ cursor: 'pointer', backgroundColor: '#1668dc' }}
              />
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ padding: 24 }}>
          <div className="page-enter">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
