import React, { useEffect, useState, useCallback } from 'react';
import {
  Tabs,
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Upload,
  Table,
  Tag,
  Switch,
  Badge,
  List,
  Segmented,
  Radio,
  Space,
  Popconfirm,
  Modal,
  Select,
  Typography,
  Divider,
  Empty,
  App,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  KeyOutlined,
  BellOutlined,
  SkinOutlined,
  FileTextOutlined,
  UploadOutlined,
  SunOutlined,
  MoonOutlined,
  DesktopOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { userApi } from '../api/user';
import { useAppStore } from '../store';
import type {
  User,
  ApiKey,
  Notification as NotificationType,
  OperationLog,
  ThemeMode,
} from '../types';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;

const CARD_STYLE: React.CSSProperties = { borderRadius: 12 };
const EXCHANGES = ['binance', 'okx', 'bybit'];

/* ──────────────── Profile Tab ──────────────── */
const ProfileTab: React.FC = () => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const user = useAppStore((s) => s.user);
  const setUser = useAppStore((s) => s.setUser);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      form.setFieldsValue({
        username: user.username,
        email: user.email,
        phone: user.phone ?? '',
      });
    }
  }, [user, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const updated = await userApi.updateProfile(values);
      setUser(updated);
      messageApi.success(t('common.updateSuccess'));
    } catch {
      // validation or API error
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card bordered={false} style={CARD_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 32 }}>
        <Upload
          showUploadList={false}
          accept="image/*"
          beforeUpload={() => false}
        >
          <Avatar
            size={80}
            src={user?.avatar_url}
            icon={!user?.avatar_url ? <UserOutlined /> : undefined}
            style={{ cursor: 'pointer', backgroundColor: '#1668dc' }}
          />
        </Upload>
        <div>
          <Text strong style={{ fontSize: 18 }}>
            {user?.username}
          </Text>
          <br />
          <Text type="secondary">{user?.email}</Text>
          <br />
          <Upload showUploadList={false} accept="image/*" beforeUpload={() => false}>
            <Button size="small" icon={<UploadOutlined />} style={{ marginTop: 8 }}>
              {t('userCenter.uploadAvatar')}
            </Button>
          </Upload>
        </div>
      </div>

      <Form form={form} layout="vertical" style={{ maxWidth: 480 }}>
        <Form.Item name="username" label={t('userCenter.username')}>
          <Input />
        </Form.Item>
        <Form.Item name="email" label={t('userCenter.email')}>
          <Input disabled />
        </Form.Item>
        <Form.Item name="phone" label={t('userCenter.phone')}>
          <Input />
        </Form.Item>
        <Form.Item>
          <Button type="primary" onClick={handleSave} loading={saving}>
            {t('userCenter.save')}
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

/* ──────────────── Security Tab ──────────────── */
const SecurityTab: React.FC = () => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const user = useAppStore((s) => s.user);
  const [pwForm] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [twoFaSetup, setTwoFaSetup] = useState<{ qr_uri?: string; secret?: string } | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [sessions, setSessions] = useState<Array<{ id: string; ip_address: string; user_agent: string; created_at: string; is_current: boolean }>>([]);

  useEffect(() => {
    userApi.getSessions().then(setSessions).catch(() => {});
  }, []);

  const handleChangePassword = async () => {
    try {
      const values = await pwForm.validateFields();
      if (values.new_password !== values.confirm_password) {
        messageApi.error(t('auth.confirmPassword'));
        return;
      }
      setSaving(true);
      await userApi.changePassword(values.current_password, values.new_password);
      messageApi.success(t('common.updateSuccess'));
      pwForm.resetFields();
    } catch {
      // validation or API error
    } finally {
      setSaving(false);
    }
  };

  const handleEnable2FA = async () => {
    try {
      const data = await userApi.enable2FA();
      setTwoFaSetup(data);
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const handleVerify2FA = async () => {
    try {
      await userApi.verify2FA(verifyCode);
      messageApi.success(t('userCenter.enableSuccess'));
      setTwoFaSetup(null);
      setVerifyCode('');
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const handleDisable2FA = async () => {
    try {
      await userApi.disable2FA(verifyCode);
      messageApi.success(t('userCenter.disableSuccess'));
      setVerifyCode('');
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const handleRevokeSession = async (id: string) => {
    try {
      await userApi.revokeSession(id);
      messageApi.success(t('common.operationSuccess'));
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Change Password */}
      <Card title={t('userCenter.changePassword')} bordered={false} style={CARD_STYLE}>
        <Form form={pwForm} layout="vertical" style={{ maxWidth: 400 }}>
          <Form.Item
            name="current_password"
            label={t('userCenter.currentPassword')}
            rules={[{ required: true }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="new_password"
            label={t('userCenter.newPassword')}
            rules={[{ required: true, min: 6 }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label={t('userCenter.confirmNewPassword')}
            rules={[{ required: true }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleChangePassword} loading={saving}>
              {t('common.confirm')}
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 2FA */}
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            {t('userCenter.twoFA')}
          </Space>
        }
        bordered={false}
        style={CARD_STYLE}
      >
        {user?.two_fa_enabled ? (
          <div>
            <Tag color="green" icon={<CheckCircleOutlined />}>
              {t('common.enable')}
            </Tag>
            <Divider />
            <Space>
              <Input
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                placeholder={t('userCenter.verifyCode')}
                style={{ width: 200 }}
              />
              <Button danger onClick={handleDisable2FA}>
                {t('userCenter.disable2FA')}
              </Button>
            </Space>
          </div>
        ) : twoFaSetup ? (
          <div>
            <Paragraph>{t('userCenter.qrCode')}</Paragraph>
            {twoFaSetup.qr_uri && (
              <div style={{ marginBottom: 16 }}>
                <img src={twoFaSetup.qr_uri} alt="2FA QR Code" style={{ width: 200 }} />
              </div>
            )}
            {twoFaSetup.secret && (
              <Paragraph copyable code>
                {twoFaSetup.secret}
              </Paragraph>
            )}
            <Space style={{ marginTop: 16 }}>
              <Input
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                placeholder={t('userCenter.verifyCode')}
                style={{ width: 200 }}
              />
              <Button type="primary" onClick={handleVerify2FA}>
                {t('common.confirm')}
              </Button>
              <Button onClick={() => setTwoFaSetup(null)}>{t('common.cancel')}</Button>
            </Space>
          </div>
        ) : (
          <Button type="primary" onClick={handleEnable2FA}>
            {t('userCenter.enable2FA')}
          </Button>
        )}
      </Card>

      {/* Sessions */}
      <Card title={t('userCenter.sessions')} bordered={false} style={CARD_STYLE}>
        <List
          dataSource={sessions}
          locale={{ emptyText: t('common.noData') }}
          renderItem={(session) => (
            <List.Item
              actions={
                session.is_current
                  ? [<Tag color="blue" key="current">{t('common.open')}</Tag>]
                  : [
                      <Popconfirm
                        key="revoke"
                        title={t('common.deleteConfirm')}
                        onConfirm={() => handleRevokeSession(session.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                      >
                        <Button size="small" danger>
                          {t('userCenter.revokeSession')}
                        </Button>
                      </Popconfirm>,
                    ]
              }
            >
              <List.Item.Meta
                title={session.user_agent}
                description={
                  <Space>
                    <Text type="secondary">{session.ip_address}</Text>
                    <Text type="secondary">
                      {dayjs(session.created_at).format('YYYY-MM-DD HH:mm')}
                    </Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

/* ──────────────── API Keys Tab ──────────────── */
const ApiKeysTab: React.FC = () => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    try {
      const data = await userApi.getApiKeys();
      setKeys(Array.isArray(data) ? data : data.items ?? []);
    } catch {
      // keys remain empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await userApi.createApiKey({ ...values, permissions: ['read', 'trade'] });
      messageApi.success(t('common.createSuccess'));
      setModalOpen(false);
      form.resetFields();
      fetchKeys();
    } catch {
      // validation or API error
    } finally {
      setSubmitting(false);
    }
  };

  const handleTest = async (id: string) => {
    try {
      await userApi.testApiKey(id);
      messageApi.success(t('userCenter.testSuccess'));
    } catch {
      messageApi.error(t('userCenter.testFail'));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await userApi.deleteApiKey(id);
      messageApi.success(t('common.deleteSuccess'));
      fetchKeys();
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const columns: ColumnsType<ApiKey> = [
    {
      title: t('userCenter.exchange'),
      dataIndex: 'exchange',
      key: 'exchange',
      render: (text: string) => text.charAt(0).toUpperCase() + text.slice(1),
    },
    {
      title: t('userCenter.label'),
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: t('userCenter.permissions'),
      dataIndex: 'permissions',
      key: 'permissions',
      render: (perms: string[]) =>
        perms?.map((p) => (
          <Tag key={p} color="blue">
            {p}
          </Tag>
        )),
    },
    {
      title: t('trading.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) =>
        active ? (
          <Badge status="success" text={t('common.enable')} />
        ) : (
          <Badge status="default" text={t('common.disable')} />
        ),
    },
    {
      title: '',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: ApiKey) => (
        <Space>
          <Button size="small" icon={<ApiOutlined />} onClick={() => handleTest(record.id)}>
            {t('userCenter.testConnection')}
          </Button>
          <Popconfirm
            title={t('userCenter.deleteKeyConfirm')}
            onConfirm={() => handleDelete(record.id)}
            okText={t('common.confirm')}
            cancelText={t('common.cancel')}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card bordered={false} style={CARD_STYLE}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 16 }}>
          {t('userCenter.apiKeys')}
        </Text>
        <Button type="primary" icon={<KeyOutlined />} onClick={() => setModalOpen(true)}>
          {t('userCenter.addApiKey')}
        </Button>
      </div>

      {!loading && keys.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('userCenter.noApiKeys')}>
          <Button type="primary" onClick={() => setModalOpen(true)}>
            {t('userCenter.addApiKey')}
          </Button>
        </Empty>
      ) : (
        <Table<ApiKey>
          columns={columns}
          dataSource={keys}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="middle"
        />
      )}

      <Modal
        title={t('userCenter.addApiKey')}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreate}
        confirmLoading={submitting}
        okText={t('common.confirm')}
        cancelText={t('common.cancel')}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="exchange"
            label={t('userCenter.exchange')}
            rules={[{ required: true }]}
            initialValue="binance"
          >
            <Select
              options={EXCHANGES.map((e) => ({
                label: e.charAt(0).toUpperCase() + e.slice(1),
                value: e,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="label"
            label={t('userCenter.label')}
            rules={[{ required: true }]}
          >
            <Input placeholder={t('userCenter.label')} />
          </Form.Item>
          <Form.Item
            name="api_key"
            label={t('userCenter.keyId')}
            rules={[{ required: true }]}
          >
            <Input.Password placeholder={t('userCenter.keyId')} />
          </Form.Item>
          <Form.Item
            name="api_secret"
            label={t('userCenter.keySecret')}
            rules={[{ required: true }]}
          >
            <Input.Password placeholder={t('userCenter.keySecret')} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

/* ──────────────── Notifications Tab ──────────────── */
const NotificationsTab: React.FC = () => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const setUnreadCount = useAppStore((s) => s.setUnreadCount);
  const [notifications, setNotifications] = useState<NotificationType[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await userApi.getNotifications();
      const items = Array.isArray(data) ? data : data.items ?? [];
      setNotifications(items);
      setUnreadCount(items.filter((n: NotificationType) => !n.is_read).length);
    } catch {
      // empty
    } finally {
      setLoading(false);
    }
  }, [setUnreadCount]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAllRead = async () => {
    try {
      await userApi.markAllNotificationsRead();
      messageApi.success(t('common.operationSuccess'));
      fetchNotifications();
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await userApi.markNotificationRead(id);
      fetchNotifications();
    } catch {
      // ignore
    }
  };

  return (
    <Card bordered={false} style={CARD_STYLE}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Text strong style={{ fontSize: 16 }}>
          {t('userCenter.notifications')}
        </Text>
        <Button size="small" onClick={handleMarkAllRead}>
          {t('userCenter.markAllRead')}
        </Button>
      </div>

      {!loading && notifications.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('userCenter.noNotifications')}
        />
      ) : (
        <List
          loading={loading}
          dataSource={notifications}
          renderItem={(item) => (
            <List.Item
              style={{ cursor: item.is_read ? 'default' : 'pointer' }}
              onClick={() => !item.is_read && handleMarkRead(item.id)}
            >
              <List.Item.Meta
                avatar={
                  <Badge dot={!item.is_read} offset={[-2, 2]}>
                    <BellOutlined style={{ fontSize: 20 }} />
                  </Badge>
                }
                title={
                  <Text strong={!item.is_read}>
                    {item.title}
                    {item.notification_type && (
                      <Tag style={{ marginLeft: 8 }} color="blue">
                        {item.notification_type}
                      </Tag>
                    )}
                  </Text>
                }
                description={
                  <div>
                    <Text type="secondary">{item.content}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}
                    </Text>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}

      <Divider />
      <Title level={5}>{t('userCenter.enableNotification')}</Title>
      <Space direction="vertical" size={12}>
        <div style={{ display: 'flex', justifyContent: 'space-between', width: 300 }}>
          <Text>{t('userCenter.tradeNotification')}</Text>
          <Switch defaultChecked />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', width: 300 }}>
          <Text>{t('userCenter.alertNotification')}</Text>
          <Switch defaultChecked />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', width: 300 }}>
          <Text>{t('userCenter.systemNotification')}</Text>
          <Switch defaultChecked />
        </div>
      </Space>
    </Card>
  );
};

/* ──────────────── Appearance Tab ──────────────── */
const AppearanceTab: React.FC = () => {
  const { t, i18n } = useTranslation();
  const themeMode = useAppStore((s) => s.themeMode);
  const setThemeMode = useAppStore((s) => s.setThemeMode);
  const language = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const resolvedTheme = useAppStore((s) => s.resolvedTheme);

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang as 'zh-CN' | 'en-US');
    i18n.changeLanguage(lang);
  };

  return (
    <Card bordered={false} style={CARD_STYLE}>
      <div style={{ maxWidth: 480 }}>
        <Title level={5}>{t('userCenter.themeMode')}</Title>
        <Segmented
          size="large"
          value={themeMode}
          onChange={(value) => setThemeMode(value as ThemeMode)}
          options={[
            {
              value: 'light',
              label: (
                <Space>
                  <SunOutlined />
                  {t('userCenter.light')}
                </Space>
              ),
            },
            {
              value: 'dark',
              label: (
                <Space>
                  <MoonOutlined />
                  {t('userCenter.dark')}
                </Space>
              ),
            },
            {
              value: 'auto',
              label: (
                <Space>
                  <DesktopOutlined />
                  {t('userCenter.auto')}
                </Space>
              ),
            },
          ]}
          style={{ marginBottom: 32 }}
        />

        <Divider />

        <Title level={5}>{t('userCenter.language')}</Title>
        <Radio.Group
          value={language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          style={{ marginBottom: 32 }}
        >
          <Radio.Button value="zh-CN">{t('userCenter.chinese')}</Radio.Button>
          <Radio.Button value="en-US">{t('userCenter.english')}</Radio.Button>
        </Radio.Group>

        <Divider />

        {/* Theme preview */}
        <Title level={5}>Preview</Title>
        <div
          style={{
            padding: 24,
            borderRadius: 12,
            background: resolvedTheme === 'dark' ? '#1f1f1f' : '#f5f5f5',
            border: `1px solid ${resolvedTheme === 'dark' ? '#303030' : '#d9d9d9'}`,
          }}
        >
          <Text>
            {resolvedTheme === 'dark' ? '🌙' : '☀️'} {t('userCenter.themeMode')}:{' '}
            <strong>{themeMode}</strong>
          </Text>
          <br />
          <Text type="secondary">
            Resolved: <strong>{resolvedTheme}</strong>
          </Text>
        </div>
      </div>
    </Card>
  );
};

/* ──────────────── Operation Log Tab ──────────────── */
const OperationLogTab: React.FC = () => {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<OperationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const fetchLogs = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const data = await userApi.getOperationLog(p, pageSize);
      setLogs(Array.isArray(data) ? data : data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      // empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs(page);
  }, [page, fetchLogs]);

  const columns: ColumnsType<OperationLog> = [
    {
      title: t('userCenter.operationType'),
      dataIndex: 'action',
      key: 'action',
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: 'Resource',
      dataIndex: 'resource_type',
      key: 'resource_type',
    },
    {
      title: 'Details',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
      render: (val: Record<string, unknown>) =>
        val ? JSON.stringify(val).slice(0, 80) : '—',
    },
    {
      title: t('userCenter.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: t('userCenter.operationTime'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  return (
    <Card bordered={false} style={CARD_STYLE}>
      {!loading && logs.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('userCenter.noLogs')} />
      ) : (
        <Table<OperationLog>
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          size="middle"
          pagination={{
            current: page,
            total,
            pageSize,
            onChange: setPage,
            showTotal: (tot) => `${t('common.total')} ${tot} ${t('common.items')}`,
          }}
        />
      )}
    </Card>
  );
};

/* ──────────────── Main UserCenter ──────────────── */
const UserCenter: React.FC = () => {
  const { t } = useTranslation();

  const tabItems = [
    {
      key: 'profile',
      label: (
        <span>
          <UserOutlined /> {t('userCenter.profile')}
        </span>
      ),
      children: <ProfileTab />,
    },
    {
      key: 'security',
      label: (
        <span>
          <LockOutlined /> {t('userCenter.security')}
        </span>
      ),
      children: <SecurityTab />,
    },
    {
      key: 'api-keys',
      label: (
        <span>
          <KeyOutlined /> {t('userCenter.apiKeys')}
        </span>
      ),
      children: <ApiKeysTab />,
    },
    {
      key: 'notifications',
      label: (
        <span>
          <BellOutlined /> {t('userCenter.notifications')}
        </span>
      ),
      children: <NotificationsTab />,
    },
    {
      key: 'appearance',
      label: (
        <span>
          <SkinOutlined /> {t('userCenter.appearance')}
        </span>
      ),
      children: <AppearanceTab />,
    },
    {
      key: 'operation-log',
      label: (
        <span>
          <FileTextOutlined /> {t('userCenter.operationLog')}
        </span>
      ),
      children: <OperationLogTab />,
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        {t('userCenter.title')}
      </Title>
      <Tabs items={tabItems} tabPosition="left" style={{ minHeight: 500 }} />
    </div>
  );
};

export default UserCenter;
