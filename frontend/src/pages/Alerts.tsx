import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Tag,
  Popconfirm,
  Space,
  Typography,
  Empty,
  App,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { alertsApi } from '../api/alerts';
import type { Alert } from '../types';

const { Title } = Typography;

const CARD_STYLE: React.CSSProperties = { borderRadius: 12 };

const SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'];
const EXCHANGES = ['binance', 'okx', 'bybit'];

const Alerts: React.FC = () => {
  const { t } = useTranslation();
  const { message: messageApi } = App.useApp();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await alertsApi.getAlerts();
      setAlerts(data.items);
    } catch {
      // alerts remain empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const openCreateModal = () => {
    setEditingAlert(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEditModal = (alert: Alert) => {
    setEditingAlert(alert);
    form.setFieldsValue({
      name: alert.name,
      alert_type: alert.alert_type,
      exchange: 'binance',
      symbol: alert.symbol,
      condition: alert.condition,
      threshold: alert.threshold,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingAlert) {
        await alertsApi.updateAlert(editingAlert.id, values);
        messageApi.success(t('common.updateSuccess'));
      } else {
        await alertsApi.createAlert(values);
        messageApi.success(t('common.createSuccess'));
      }
      setModalOpen(false);
      fetchAlerts();
    } catch {
      // validation or API error
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await alertsApi.deleteAlert(id);
      messageApi.success(t('common.deleteSuccess'));
      fetchAlerts();
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const handleToggle = async (alert: Alert, checked: boolean) => {
    try {
      await alertsApi.toggleAlert(alert.id, checked);
      fetchAlerts();
    } catch {
      messageApi.error(t('common.error'));
    }
  };

  const columns: ColumnsType<Alert> = [
    {
      title: t('alerts.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: t('alerts.alertType'),
      dataIndex: 'alert_type',
      key: 'alert_type',
      render: (type: string) => (
        <Tag color={type === 'price' ? 'blue' : 'purple'}>
          {type === 'price' ? t('alerts.priceAlert') : t('alerts.percentAlert')}
        </Tag>
      ),
    },
    {
      title: t('alerts.symbol'),
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: t('alerts.condition'),
      key: 'condition',
      render: (_: unknown, record: Alert) => (
        <span>
          {record.condition === 'above' ? t('alerts.above') : t('alerts.below')}{' '}
          <strong>
            {record.alert_type === 'price'
              ? `$${record.threshold.toLocaleString()}`
              : `${record.threshold}%`}
          </strong>
        </span>
      ),
    },
    {
      title: t('alerts.active'),
      key: 'status',
      render: (_: unknown, record: Alert) =>
        record.is_triggered ? (
          <Tag color="orange">{t('alerts.triggered')}</Tag>
        ) : (
          <Switch
            size="small"
            checked={record.is_active}
            onChange={(checked) => handleToggle(record, checked)}
          />
        ),
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: Alert) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          />
          <Popconfirm
            title={t('alerts.deleteConfirm')}
            onConfirm={() => handleDelete(record.id)}
            okText={t('common.confirm')}
            cancelText={t('common.cancel')}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          <BellOutlined style={{ marginRight: 8 }} />
          {t('alerts.title')}
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          {t('alerts.create')}
        </Button>
      </div>

      <Card bordered={false} className="hoverable-card" style={CARD_STYLE}>
        {!loading && alerts.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('alerts.noAlerts')}
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
              {t('alerts.create')}
            </Button>
          </Empty>
        ) : (
          <Table<Alert>
            columns={columns}
            dataSource={alerts}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            size="middle"
            locale={{ emptyText: t('common.noData') }}
          />
        )}
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingAlert ? t('alerts.edit') : t('alerts.createAlert')}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText={t('common.confirm')}
        cancelText={t('common.cancel')}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label={t('alerts.name')}
            rules={[{ required: true, message: t('alerts.name') }]}
          >
            <Input placeholder={t('alerts.name')} />
          </Form.Item>

          <Form.Item
            name="alert_type"
            label={t('alerts.alertType')}
            rules={[{ required: true }]}
            initialValue="price"
          >
            <Select
              options={[
                { label: t('alerts.priceAlert'), value: 'price' },
                { label: t('alerts.percentAlert'), value: 'percent' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="exchange"
            label={t('alerts.exchange')}
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
            name="symbol"
            label={t('alerts.symbol')}
            rules={[{ required: true }]}
          >
            <Select
              showSearch
              options={SYMBOLS.map((s) => ({ label: s, value: s }))}
              placeholder={t('alerts.symbol')}
            />
          </Form.Item>

          <Form.Item
            name="condition"
            label={t('alerts.condition')}
            rules={[{ required: true }]}
            initialValue="above"
          >
            <Select
              options={[
                { label: t('alerts.above'), value: 'above' },
                { label: t('alerts.below'), value: 'below' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="threshold"
            label={t('alerts.threshold')}
            rules={[{ required: true, message: t('alerts.threshold') }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              step={0.01}
              placeholder={t('alerts.threshold')}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Alerts;
