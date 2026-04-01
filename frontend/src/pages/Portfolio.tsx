import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, Spin, Empty } from 'antd';
import {
  WalletOutlined,
  DollarOutlined,
  RiseOutlined,
  FundOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { tradingApi } from '../api/trading';
import type { Portfolio as PortfolioType, Position } from '../types';
import PriceChange from '../components/Common/PriceChange';

const { Title, Text } = Typography;

const CARD_STYLE: React.CSSProperties = { borderRadius: 12 };

const Portfolio: React.FC = () => {
  const { t } = useTranslation();
  const [portfolio, setPortfolio] = useState<PortfolioType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await tradingApi.getPortfolio();
        setPortfolio(data);
      } catch {
        // portfolio stays null on error
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const dailyPnl = portfolio?.daily_pnl ?? 0;
  const totalPnl = portfolio?.total_pnl ?? 0;
  const isDailyPositive = dailyPnl >= 0;
  const isTotalPositive = totalPnl >= 0;

  const statCards = [
    {
      title: t('portfolio.totalValue'),
      value: portfolio?.total_value_usdt ?? 0,
      prefix: '$',
      className: 'stat-card-blue',
      icon: <WalletOutlined />,
    },
    {
      title: t('portfolio.availableBalance'),
      value: portfolio?.available_usdt ?? 0,
      prefix: '$',
      className: 'stat-card-gold',
      icon: <DollarOutlined />,
    },
    {
      title: t('portfolio.dailyPnl'),
      value: Math.abs(dailyPnl),
      prefix: isDailyPositive ? '+$' : '-$',
      className: isDailyPositive ? 'stat-card-green' : 'stat-card-red',
      icon: isDailyPositive ? <ArrowUpOutlined /> : <ArrowDownOutlined />,
    },
    {
      title: t('portfolio.totalPnl'),
      value: Math.abs(totalPnl),
      prefix: isTotalPositive ? '+$' : '-$',
      className: isTotalPositive ? 'stat-card-green' : 'stat-card-red',
      icon: <RiseOutlined />,
    },
  ];

  const positionColumns: ColumnsType<Position> = [
    {
      title: t('portfolio.symbol'),
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: t('portfolio.quantity'),
      dataIndex: 'quantity',
      key: 'quantity',
      render: (v: number) =>
        v.toLocaleString(undefined, {
          minimumFractionDigits: 4,
          maximumFractionDigits: 8,
        }),
    },
    {
      title: t('portfolio.avgPrice'),
      dataIndex: 'avg_price',
      key: 'avg_price',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('portfolio.currentPrice'),
      dataIndex: 'current_price',
      key: 'current_price',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('portfolio.unrealizedPnl'),
      dataIndex: 'pnl',
      key: 'pnl',
      render: (v: number) => <PriceChange value={v} />,
    },
    {
      title: '%',
      dataIndex: 'pnl_pct',
      key: 'pnl_pct',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#26a69a' : '#ef5350', fontWeight: 500 }}>
          {v >= 0 ? '+' : ''}
          {v.toFixed(2)}%
        </span>
      ),
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
      <Title level={4} style={{ marginBottom: 24 }}>
        <FundOutlined style={{ marginRight: 8 }} />
        {t('portfolio.title')}
      </Title>

      {/* Stat Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statCards.map((card) => (
          <Col xs={24} sm={12} lg={6} key={card.title}>
            <Card
              className="hoverable-card"
              bodyStyle={{ padding: 0 }}
              bordered={false}
              style={CARD_STYLE}
            >
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
                    value={card.value}
                    prefix={card.prefix}
                    valueStyle={{ color: '#fff', fontSize: 22, fontWeight: 700 }}
                    precision={2}
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

      {/* Positions Table */}
      <Card
        title={t('portfolio.positions')}
        bordered={false}
        className="hoverable-card"
        style={CARD_STYLE}
      >
        {portfolio?.positions && portfolio.positions.length > 0 ? (
          <Table<Position>
            columns={positionColumns}
            dataSource={portfolio.positions}
            rowKey="symbol"
            pagination={false}
            size="middle"
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('portfolio.noPositions')}
          />
        )}
      </Card>
    </div>
  );
};

export default Portfolio;
