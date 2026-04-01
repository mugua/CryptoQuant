import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Table,
  Tag,
  Spin,
  Typography,
  message,
} from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { strategiesApi } from '../api/strategies';
import type { BacktestResult } from '../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const STRATEGY_TYPES = [
  { value: 'MA_CROSS', labelKey: 'strategies.maStrategy' },
  { value: 'RSI', labelKey: 'strategies.rsiStrategy' },
  { value: 'MACD', labelKey: 'MACD' },
  { value: 'BOLLINGER', labelKey: 'strategies.bbStrategy' },
];

const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'];

interface TradeRecord {
  entry_time: string;
  exit_time: string;
  side: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  return_pct: number;
}

const Backtest: React.FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const handleRun = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      setResult(null);

      const [startDate, endDate] = values.dateRange;
      const params = {
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD'),
        initial_capital: values.initial_capital,
        commission: values.commission,
        slippage: values.slippage,
      };

      const data = await strategiesApi.runBacktest(values.strategy_type, params);
      setResult(data as BacktestResult);
      message.success(t('common.operationSuccess'));
    } catch {
      message.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const statCards = result
    ? [
        {
          title: t('backtest.totalReturn'),
          value: result.total_return,
          suffix: '%',
          color: result.total_return >= 0 ? '#26a69a' : '#ef5350',
        },
        {
          title: t('backtest.annualReturn'),
          value: result.annualized_return,
          suffix: '%',
          color: result.annualized_return >= 0 ? '#26a69a' : '#ef5350',
        },
        {
          title: t('backtest.sharpeRatio'),
          value: result.sharpe_ratio,
          suffix: '',
          color: undefined,
        },
        {
          title: t('backtest.maxDrawdown'),
          value: result.max_drawdown,
          suffix: '%',
          color: '#ef5350',
        },
        {
          title: t('backtest.winRate'),
          value: result.win_rate,
          suffix: '%',
          color: undefined,
        },
        {
          title: t('backtest.profitFactor'),
          value: result.profit_factor,
          suffix: '',
          color: undefined,
        },
      ]
    : [];

  const tradeColumns: ColumnsType<TradeRecord> = [
    {
      title: t('backtest.entryTime'),
      dataIndex: 'entry_time',
      key: 'entry_time',
      width: 170,
    },
    {
      title: t('backtest.exitTime'),
      dataIndex: 'exit_time',
      key: 'exit_time',
      width: 170,
    },
    {
      title: t('backtest.side'),
      dataIndex: 'side',
      key: 'side',
      width: 80,
      render: (side: string) => (
        <Tag color={side === 'buy' ? 'green' : 'red'}>
          {side === 'buy' ? t('common.buy') : t('common.sell')}
        </Tag>
      ),
    },
    {
      title: t('backtest.entryPrice'),
      dataIndex: 'entry_price',
      key: 'entry_price',
      render: (v: number) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('backtest.exitPrice'),
      dataIndex: 'exit_price',
      key: 'exit_price',
      render: (v: number) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('backtest.pnl'),
      dataIndex: 'pnl',
      key: 'pnl',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#26a69a' : '#ef5350', fontWeight: 500 }}>
          {v >= 0 ? '+' : ''}
          ${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      title: t('backtest.returnPct'),
      dataIndex: 'return_pct',
      key: 'return_pct',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#26a69a' : '#ef5350', fontWeight: 500 }}>
          {v >= 0 ? '+' : ''}
          {v.toFixed(2)}%
        </span>
      ),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        {t('backtest.title')}
      </Title>

      {/* Configuration */}
      <Card
        style={{ borderRadius: 12, marginBottom: 24 }}
        bordered={false}
        className="hoverable-card"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            exchange: 'binance',
            symbol: 'BTC/USDT',
            initial_capital: 10000,
            commission: 0.001,
            slippage: 0.001,
          }}
        >
          <Row gutter={16}>
            <Col xs={24} md={12} lg={6}>
              <Form.Item
                name="strategy_type"
                label={t('backtest.strategyType')}
                rules={[{ required: true, message: t('backtest.selectStrategy') }]}
              >
                <Select placeholder={t('backtest.selectStrategy')}>
                  {STRATEGY_TYPES.map((st) => (
                    <Select.Option key={st.value} value={st.value}>
                      {st.labelKey.startsWith('strategies.') ? t(st.labelKey) : st.labelKey}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item
                name="exchange"
                label={t('backtest.exchange')}
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item
                name="symbol"
                label={t('backtest.symbol')}
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item
                name="timeframe"
                label={t('backtest.timeframe')}
                rules={[{ required: true }]}
              >
                <Select>
                  {TIMEFRAMES.map((tf) => (
                    <Select.Option key={tf} value={tf}>
                      {tf}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} md={12} lg={6}>
              <Form.Item
                name="dateRange"
                label={`${t('backtest.startDate')} - ${t('backtest.endDate')}`}
                rules={[{ required: true }]}
              >
                <RangePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12} lg={6}>
              <Form.Item
                name="initial_capital"
                label={t('backtest.initialCapital')}
                rules={[{ required: true }]}
              >
                <InputNumber min={100} style={{ width: '100%' }} prefix="$" />
              </Form.Item>
            </Col>
            <Col xs={12} md={6} lg={6}>
              <Form.Item name="commission" label={t('backtest.commission')}>
                <InputNumber min={0} step={0.0001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={12} md={6} lg={6}>
              <Form.Item name="slippage" label={t('backtest.slippage')}>
                <InputNumber min={0} step={0.0001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Button
            type="primary"
            icon={<ExperimentOutlined />}
            onClick={handleRun}
            loading={loading}
            size="large"
          >
            {loading ? t('backtest.running') : t('backtest.run')}
          </Button>
        </Form>
      </Card>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" tip={t('backtest.running')} />
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Stat Cards */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            {statCards.map((stat) => (
              <Col xs={12} md={8} lg={4} key={stat.title}>
                <Card
                  className="hoverable-card"
                  style={{ borderRadius: 12, textAlign: 'center' }}
                  bordered={false}
                  bodyStyle={{ padding: '20px 12px' }}
                >
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    {stat.title}
                  </Text>
                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 700,
                      marginTop: 8,
                      color: stat.color,
                    }}
                  >
                    {typeof stat.value === 'number' ? stat.value.toFixed(2) : stat.value}
                    {stat.suffix}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>

          {/* Trade History */}
          <Card
            title={t('backtest.tradeHistory')}
            style={{ borderRadius: 12 }}
            bordered={false}
            className="hoverable-card"
          >
            <Table<TradeRecord>
              columns={tradeColumns}
              dataSource={result.trades}
              rowKey={(_, index) => String(index)}
              pagination={{ pageSize: 10, showSizeChanger: true }}
              size="small"
              scroll={{ x: 800 }}
              locale={{ emptyText: t('common.noData') }}
            />
          </Card>
        </>
      )}
    </div>
  );
};

export default Backtest;
