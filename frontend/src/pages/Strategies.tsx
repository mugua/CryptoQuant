import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Empty,
  Spin,
  Popconfirm,
  Typography,
  Descriptions,
  message,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  ExperimentOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { strategiesApi } from '../api/strategies';
import type { Strategy } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const STRATEGY_TYPES = [
  { value: 'MA_CROSS', labelKey: 'strategies.maStrategy' },
  { value: 'RSI', labelKey: 'strategies.rsiStrategy' },
  { value: 'BOLLINGER', labelKey: 'strategies.bbStrategy' },
  { value: 'GRID', labelKey: 'strategies.gridStrategy' },
  { value: 'DCA', labelKey: 'strategies.dcaStrategy' },
];

const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'];

const Strategies: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchStrategies = useCallback(async () => {
    setLoading(true);
    try {
      const data = await strategiesApi.list();
      setStrategies(data.items);
    } catch {
      message.error(t('common.networkError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const openCreateModal = () => {
    setEditingStrategy(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openEditModal = (strategy: Strategy) => {
    setEditingStrategy(strategy);
    form.setFieldsValue({
      name: strategy.name,
      description: strategy.description,
      strategy_type: strategy.strategy_type,
      exchange: strategy.exchange,
      symbol: strategy.symbol,
      timeframe: strategy.timeframe,
      parameters: JSON.stringify(strategy.parameters, null, 2),
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      let params: Record<string, unknown> = {};
      if (values.parameters) {
        try {
          params = JSON.parse(values.parameters);
        } catch {
          message.error(t('common.error'));
          setSubmitting(false);
          return;
        }
      }

      const payload = { ...values, parameters: params };

      if (editingStrategy) {
        await strategiesApi.update(editingStrategy.id, payload);
        message.success(t('common.updateSuccess'));
      } else {
        await strategiesApi.create(payload);
        message.success(t('common.createSuccess'));
      }

      setModalVisible(false);
      fetchStrategies();
    } catch {
      // validation failed
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await strategiesApi.delete(id);
      message.success(t('common.deleteSuccess'));
      fetchStrategies();
    } catch {
      message.error(t('common.error'));
    }
  };

  const handleToggle = async (strategy: Strategy) => {
    try {
      if (strategy.is_running) {
        await strategiesApi.stop(strategy.id);
      } else {
        await strategiesApi.start(strategy.id);
      }
      message.success(t('common.operationSuccess'));
      fetchStrategies();
    } catch {
      message.error(t('common.error'));
    }
  };

  const handleBacktest = (strategy: Strategy) => {
    navigate('/backtest', { state: { strategyId: strategy.id, strategyType: strategy.strategy_type } });
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          {t('strategies.title')}
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          {t('strategies.create')}
        </Button>
      </div>

      {strategies.length === 0 ? (
        <Card style={{ borderRadius: 12 }} bordered={false}>
          <Empty description={t('strategies.noStrategies')} />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {strategies.map((strategy) => (
            <Col xs={24} md={12} lg={8} key={strategy.id}>
              <Card
                className="hoverable-card"
                style={{ borderRadius: 12, height: '100%' }}
                bordered={false}
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Text strong ellipsis style={{ flex: 1 }}>
                      {strategy.name}
                    </Text>
                    <Tag color={strategy.is_running ? 'green' : 'default'}>
                      {strategy.is_running ? t('strategies.running') : t('strategies.stopped')}
                    </Tag>
                  </div>
                }
                actions={[
                  <EditOutlined key="edit" onClick={() => openEditModal(strategy)} />,
                  <ExperimentOutlined key="backtest" onClick={() => handleBacktest(strategy)} />,
                  strategy.is_running ? (
                    <PauseCircleOutlined key="toggle" onClick={() => handleToggle(strategy)} />
                  ) : (
                    <PlayCircleOutlined key="toggle" onClick={() => handleToggle(strategy)} />
                  ),
                  <Popconfirm
                    key="delete"
                    title={t('strategies.deleteConfirm')}
                    onConfirm={() => handleDelete(strategy.id)}
                    okText={t('common.confirm')}
                    cancelText={t('common.cancel')}
                  >
                    <DeleteOutlined style={{ color: '#ff4d4f' }} />
                  </Popconfirm>,
                ]}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label={t('strategies.strategyType')}>
                    {strategy.strategy_type}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('strategies.exchange')}>
                    {strategy.exchange}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('strategies.symbol')}>
                    {strategy.symbol}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('strategies.timeframe')}>
                    {strategy.timeframe}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title={editingStrategy ? t('strategies.editStrategy') : t('strategies.createStrategy')}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        okText={t('strategies.confirm')}
        cancelText={t('strategies.cancel')}
        destroyOnClose
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label={t('strategies.name')}
            rules={[{ required: true, message: t('strategies.name') }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label={t('strategies.description')}>
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item
            name="strategy_type"
            label={t('strategies.strategyType')}
            rules={[{ required: true, message: t('strategies.strategyType') }]}
          >
            <Select>
              {STRATEGY_TYPES.map((st) => (
                <Select.Option key={st.value} value={st.value}>
                  {t(st.labelKey)}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="exchange"
                label={t('strategies.exchange')}
                rules={[{ required: true, message: t('strategies.exchange') }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="symbol"
                label={t('strategies.symbol')}
                rules={[{ required: true, message: t('strategies.symbol') }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="timeframe"
            label={t('strategies.timeframe')}
            rules={[{ required: true, message: t('strategies.timeframe') }]}
          >
            <Select>
              {TIMEFRAMES.map((tf) => (
                <Select.Option key={tf} value={tf}>
                  {tf}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="parameters" label={t('strategies.parameters')}>
            <TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Strategies;
