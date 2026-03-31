import React, { useState } from 'react';
import { Form, Input, Button, Tabs, message } from 'antd';
import {
  MailOutlined,
  LockOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { authApi } from '../api/auth';
import { useAppStore } from '../store';

const Login: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setTokens = useAppStore((s) => s.setTokens);
  const setUser = useAppStore((s) => s.setUser);
  const [activeTab, setActiveTab] = useState('login');
  const [loginLoading, setLoginLoading] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);

  const handleLogin = async (values: { email: string; password: string }) => {
    setLoginLoading(true);
    try {
      const res = await authApi.login(values);
      setTokens(res.access_token, res.refresh_token);
      const user = await authApi.me();
      setUser(user);
      message.success(t('common.success'));
      navigate('/dashboard');
    } catch {
      message.error(t('common.error'));
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegister = async (values: {
    email: string;
    username: string;
    password: string;
  }) => {
    setRegisterLoading(true);
    try {
      await authApi.register(values);
      message.success(t('common.success'));
      setActiveTab('login');
    } catch {
      message.error(t('common.error'));
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(180deg, #0a0a0a 0%, #0d1117 50%, #0a0f1e 100%)',
        position: 'relative',
      }}
    >
      {/* Dot grid background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          position: 'relative',
          zIndex: 1,
          width: '100%',
          maxWidth: 420,
          padding: '0 16px',
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 56,
              height: 56,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #42a5f5, #7c4dff)',
              marginBottom: 16,
            }}
          >
            <ThunderboltOutlined style={{ fontSize: 28, color: '#fff' }} />
          </div>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 700,
              margin: '0 0 4px',
              background: 'linear-gradient(135deg, #42a5f5 0%, #7c4dff 50%, #26a69a 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            CryptoQuant
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.45)', margin: 0, fontSize: 14 }}>
            {t('dashboard.welcomeSubtitle')}
          </p>
        </div>

        {/* Card */}
        <div
          style={{
            background: 'rgba(255,255,255,0.04)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 16,
            padding: '32px 28px',
            boxShadow: '0 16px 48px rgba(0,0,0,0.4)',
          }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            centered
            items={[
              {
                key: 'login',
                label: t('auth.login'),
                children: (
                  <Form onFinish={handleLogin} layout="vertical" size="large">
                    <Form.Item
                      name="email"
                      rules={[
                        { required: true, message: t('auth.emailPlaceholder') },
                        { type: 'email', message: t('auth.emailPlaceholder') },
                      ]}
                    >
                      <Input
                        prefix={<MailOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder={t('auth.emailPlaceholder')}
                      />
                    </Form.Item>
                    <Form.Item
                      name="password"
                      rules={[{ required: true, message: t('auth.passwordPlaceholder') }]}
                    >
                      <Input.Password
                        prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder={t('auth.passwordPlaceholder')}
                      />
                    </Form.Item>
                    <Form.Item style={{ marginBottom: 0 }}>
                      <Button
                        type="primary"
                        htmlType="submit"
                        block
                        loading={loginLoading}
                        style={{
                          height: 44,
                          fontWeight: 600,
                          background: 'linear-gradient(135deg, #1668dc, #7c4dff)',
                          border: 'none',
                        }}
                      >
                        {t('auth.loginBtn')}
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: t('auth.register'),
                children: (
                  <Form onFinish={handleRegister} layout="vertical" size="large">
                    <Form.Item
                      name="email"
                      rules={[
                        { required: true, message: t('auth.emailPlaceholder') },
                        { type: 'email', message: t('auth.emailPlaceholder') },
                      ]}
                    >
                      <Input
                        prefix={<MailOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder={t('auth.emailPlaceholder')}
                      />
                    </Form.Item>
                    <Form.Item
                      name="username"
                      rules={[{ required: true, message: t('auth.usernamePlaceholder') }]}
                    >
                      <Input
                        prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder={t('auth.usernamePlaceholder')}
                      />
                    </Form.Item>
                    <Form.Item
                      name="password"
                      rules={[
                        { required: true, message: t('auth.passwordPlaceholder') },
                        { min: 8, message: t('auth.passwordPlaceholder') },
                      ]}
                    >
                      <Input.Password
                        prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder={t('auth.passwordPlaceholder')}
                      />
                    </Form.Item>
                    <Form.Item style={{ marginBottom: 0 }}>
                      <Button
                        type="primary"
                        htmlType="submit"
                        block
                        loading={registerLoading}
                        style={{
                          height: 44,
                          fontWeight: 600,
                          background: 'linear-gradient(135deg, #1668dc, #7c4dff)',
                          border: 'none',
                        }}
                      >
                        {t('auth.registerBtn')}
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
            ]}
          />
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          position: 'absolute',
          bottom: 24,
          color: 'rgba(255,255,255,0.25)',
          fontSize: 13,
        }}
      >
        © 2024 CryptoQuant
      </div>
    </div>
  );
};

export default Login;
