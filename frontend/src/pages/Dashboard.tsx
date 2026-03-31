import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Button, Tag, Spin, Typography } from 'antd';
import {
  LineChartOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RobotOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { tradingApi } from '../api/trading';
import type { Portfolio, Trade } from '../types';
import PriceChange from '../components/Common/PriceChange';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [portfolioData, tradesData] = await Promise.all([
          tradingApi.getPortfolio(),
          tradingApi.getTrades({ page_size: 5 }),
        ]);
        setPortfolio(portfolioData);
        setTrades(tradesData.items);
      } catch {
        // data will remain empty on error
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const tradeColumns: ColumnsType<Trade> = [
    {
      title: t('market.symbol'),
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: t('trading.side'),
      dataIndex: 'side',
      key: 'side',
      render: (side: 'buy' | 'sell') => (
        <Tag color={side === 'buy' ? 'green' : 'red'}>
          {side === 'buy' ? t('common.buy') : t('common.sell')}
        </Tag>
      ),
    },
    {
      title: t('trading.price'),
      dataIndex: 'price',
      key: 'price',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('backtest.pnl'),
      dataIndex: 'pnl',
      key: 'pnl',
      render: (v: number) => <PriceChange value={v} />,
    },
  ];

  const dailyPnl = portfolio?.daily_pnl ?? 0;
  const isPositivePnl = dailyPnl >= 0;

  const statCards = [
    {
      title: t('dashboard.totalAssets'),
      value: portfolio?.total_value_usdt ?? 0,
      prefix: '$',
      className: 'stat-card-blue',
      icon: <LineChartOutlined />,
    },
    {
      title: t('dashboard.dailyPnl'),
      value: dailyPnl,
      prefix: isPositivePnl ? '+$' : '-$',
      displayValue: Math.abs(dailyPnl),
      className: isPositivePnl ? 'stat-card-green' : 'stat-card-red',
      icon: isPositivePnl ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
    },
    {
      title: t('dashboard.activeStrategies'),
      value: 0,
      className: 'stat-card-gold',
      icon: <RobotOutlined />,
    },
    {
      title: t('dashboard.openPositions'),
      value: portfolio?.positions?.length ?? 0,
      className: 'stat-card-blue',
      icon: <SwapOutlined />,
    },
  ];

  const quickActions = [
    {
      label: t('nav.strategies'),
      path: '/strategies',
      color: '#1668dc',
      bg: 'rgba(22,104,220,0.12)',
    },
    {
      label: t('nav.backtest'),
      path: '/backtest',
      color: '#26a69a',
      bg: 'rgba(38,166,154,0.12)',
    },
    {
      label: t('nav.trading'),
      path: '/trading',
      color: '#ffa726',
      bg: 'rgba(255,167,38,0.12)',
    },
    {
      label: t('nav.market'),
      path: '/market',
      color: '#7c4dff',
      bg: 'rgba(124,77,255,0.12)',
    },
  ];

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          {t('dashboard.title')}
        </Title>
        <Text type="secondary">{t('dashboard.welcomeSubtitle')}</Text>
      </div>

      {/* Stat Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statCards.map((card) => (
          <Col xs={24} sm={12} lg={6} key={card.title}>
            <Card className="hoverable-card" bodyStyle={{ padding: 0 }} bordered={false}>
              <div className={card.className}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Statistic
                    title={
                      <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>
                        {card.title}
                      </span>
                    }
                    value={card.displayValue ?? card.value}
                    prefix={card.prefix}
                    valueStyle={{ color: '#fff', fontSize: 22, fontWeight: 700 }}
                    precision={card.prefix?.includes('$') ? 2 : 0}
                  />
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 12,
                      background: 'rgba(255,255,255,0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 20,
                      color: '#fff',
                    }}
                  >
                    {card.icon}
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Bottom Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            title={t('dashboard.recentTrades')}
            className="hoverable-card"
            bordered={false}
          >
            <Table<Trade>
              columns={tradeColumns}
              dataSource={trades}
              rowKey="id"
              pagination={false}
              size="small"
              locale={{ emptyText: t('common.noData') }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card
            title={t('dashboard.quickActions')}
            className="hoverable-card"
            bordered={false}
          >
            <Row gutter={[12, 12]}>
              {quickActions.map((action) => (
                <Col span={12} key={action.path}>
                  <Button
                    block
                    size="large"
                    onClick={() => navigate(action.path)}
                    style={{
                      height: 64,
                      borderRadius: 12,
                      fontWeight: 600,
                      color: action.color,
                      background: action.bg,
                      border: 'none',
                    }}
                  >
                    {action.label}
                  </Button>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
