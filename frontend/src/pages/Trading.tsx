import React, { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Table,
  Tag,
  Tabs,
  Form,
  Input,
  InputNumber,
  Radio,
  Typography,
  Spin,
  message,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { tradingApi } from '../api/trading';
import type { Order } from '../types';

const { Title, Text } = Typography;

const Trading: React.FC = () => {
  const { t } = useTranslation();
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderTotal, setOrderTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('open');
  const [placing, setPlacing] = useState(false);
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [form] = Form.useForm();

  const orderType = Form.useWatch('order_type', form);
  const price = Form.useWatch('price', form);
  const quantity = Form.useWatch('quantity', form);
  const total = (price && quantity) ? price * quantity : 0;

  const fetchOrders = useCallback(
    async (page = 1) => {
      setLoading(true);
      try {
        const params: { status?: string; page: number; page_size: number } = {
          page,
          page_size: 10,
        };
        if (activeTab === 'open') {
          params.status = 'pending';
        }
        const data = await tradingApi.getOrders(params);
        setOrders(data.items);
        setOrderTotal(data.total);
      } catch {
        message.error(t('common.networkError'));
      } finally {
        setLoading(false);
      }
    },
    [activeTab, t],
  );

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleCancel = async (orderId: string) => {
    try {
      await tradingApi.cancelOrder(orderId);
      message.success(t('common.operationSuccess'));
      fetchOrders();
    } catch {
      message.error(t('common.error'));
    }
  };

  const handlePlaceOrder = async () => {
    try {
      const values = await form.validateFields();
      setPlacing(true);
      await tradingApi.placeOrder({
        exchange: values.exchange,
        symbol: values.symbol,
        side,
        order_type: values.order_type,
        quantity: values.quantity,
        price: values.order_type === 'limit' ? values.price : undefined,
      });
      message.success(t('common.operationSuccess'));
      form.setFieldsValue({ price: undefined, quantity: undefined });
      fetchOrders();
    } catch {
      message.error(t('common.error'));
    } finally {
      setPlacing(false);
    }
  };

  const statusColorMap: Record<string, string> = {
    filled: 'green',
    pending: 'orange',
    canceled: 'red',
    cancelled: 'red',
    partial: 'blue',
  };

  const statusLabelMap: Record<string, string> = {
    filled: t('trading.filled'),
    pending: t('trading.pending'),
    canceled: t('trading.canceled'),
    cancelled: t('trading.canceled'),
  };

  const columns: ColumnsType<Order> = [
    {
      title: t('trading.symbol'),
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: t('trading.side'),
      dataIndex: 'side',
      key: 'side',
      width: 80,
      render: (s: 'buy' | 'sell') => (
        <Tag color={s === 'buy' ? 'green' : 'red'}>
          {s === 'buy' ? t('common.buy') : t('common.sell')}
        </Tag>
      ),
    },
    {
      title: t('trading.orderType'),
      dataIndex: 'order_type',
      key: 'order_type',
      width: 90,
      render: (v: string) => (v === 'market' ? t('trading.market') : t('trading.limit')),
    },
    {
      title: t('trading.price'),
      dataIndex: 'price',
      key: 'price',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('trading.quantity'),
      dataIndex: 'quantity',
      key: 'quantity',
    },
    {
      title: t('trading.filled'),
      dataIndex: 'filled_quantity',
      key: 'filled_quantity',
    },
    {
      title: t('trading.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColorMap[status] ?? 'default'}>
          {statusLabelMap[status] ?? status}
        </Tag>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: Order) =>
        record.status === 'pending' ? (
          <Button type="link" danger size="small" onClick={() => handleCancel(record.id)}>
            {t('trading.cancel')}
          </Button>
        ) : null,
    },
  ];

  const isBuy = side === 'buy';
  const symbolValue: string = Form.useWatch('symbol', form) ?? 'BTC';
  const symbolBase = symbolValue.split('/')[0] || symbolValue;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        {t('trading.title')}
      </Title>

      <Row gutter={[16, 16]}>
        {/* Left: Order History */}
        <Col xs={24} lg={16}>
          <Card
            style={{ borderRadius: 12 }}
            bordered={false}
            className="hoverable-card"
            extra={
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => fetchOrders()}
              >
                {t('common.refresh')}
              </Button>
            }
          >
            <Tabs
              activeKey={activeTab}
              onChange={(key) => setActiveTab(key)}
              items={[
                { key: 'open', label: t('trading.openOrders') },
                { key: 'history', label: t('trading.orderHistory') },
              ]}
            />
            {loading ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin />
              </div>
            ) : (
              <Table<Order>
                columns={columns}
                dataSource={orders}
                rowKey="id"
                size="small"
                scroll={{ x: 700 }}
                locale={{ emptyText: t('common.noData') }}
                pagination={{
                  total: orderTotal,
                  pageSize: 10,
                  showSizeChanger: false,
                  onChange: (page) => fetchOrders(page),
                }}
              />
            )}
          </Card>
        </Col>

        {/* Right: Place Order */}
        <Col xs={24} lg={8}>
          <Card
            title={t('trading.placeOrder')}
            style={{ borderRadius: 12, position: 'sticky', top: 16 }}
            bordered={false}
            className="hoverable-card"
          >
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                exchange: 'binance',
                symbol: 'BTC/USDT',
                order_type: 'limit',
              }}
            >
              <Form.Item
                name="exchange"
                label={t('trading.exchange')}
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>

              <Form.Item
                name="symbol"
                label={t('trading.symbol')}
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>

              {/* Buy / Sell toggle */}
              <Form.Item label={t('trading.side')}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Button
                    block
                    size="large"
                    type={isBuy ? 'primary' : 'default'}
                    style={{
                      background: isBuy ? '#26a69a' : undefined,
                      borderColor: isBuy ? '#26a69a' : undefined,
                      fontWeight: 600,
                    }}
                    onClick={() => setSide('buy')}
                  >
                    {t('trading.buy')}
                  </Button>
                  <Button
                    block
                    size="large"
                    type={!isBuy ? 'primary' : 'default'}
                    style={{
                      background: !isBuy ? '#ef5350' : undefined,
                      borderColor: !isBuy ? '#ef5350' : undefined,
                      fontWeight: 600,
                    }}
                    onClick={() => setSide('sell')}
                  >
                    {t('trading.sell')}
                  </Button>
                </div>
              </Form.Item>

              <Form.Item name="order_type" label={t('trading.orderType')}>
                <Radio.Group>
                  <Radio.Button value="market">{t('trading.market')}</Radio.Button>
                  <Radio.Button value="limit">{t('trading.limit')}</Radio.Button>
                </Radio.Group>
              </Form.Item>

              <Form.Item
                name="price"
                label={t('trading.price')}
                rules={orderType === 'limit' ? [{ required: true }] : []}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  disabled={orderType === 'market'}
                  prefix="$"
                />
              </Form.Item>

              <Form.Item
                name="quantity"
                label={t('trading.quantity')}
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>

              {/* Total display */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '8px 0 16px',
                  borderTop: '1px solid rgba(128,128,128,0.15)',
                }}
              >
                <Text type="secondary">{t('trading.total')}</Text>
                <Text strong>
                  ${total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </Text>
              </div>

              <Button
                block
                size="large"
                type="primary"
                loading={placing}
                onClick={handlePlaceOrder}
                style={{
                  height: 48,
                  fontWeight: 700,
                  fontSize: 16,
                  background: isBuy ? '#26a69a' : '#ef5350',
                  borderColor: isBuy ? '#26a69a' : '#ef5350',
                }}
              >
                {isBuy
                  ? `${t('trading.buy')} ${symbolBase}`
                  : `${t('trading.sell')} ${symbolBase}`}
              </Button>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Trading;
