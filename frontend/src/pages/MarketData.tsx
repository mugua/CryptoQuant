import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Select, Table, Typography, Spin, Space } from 'antd';
import { useTranslation } from 'react-i18next';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import type { ColumnsType } from 'antd/es/table';
import { marketApi } from '../api/market';
import { getChartTheme } from '../themes';
import { useAppStore } from '../store';
import type { MarketTicker } from '../types';
import PriceChange from '../components/Common/PriceChange';

const { Title, Text } = Typography;

const SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'];
const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d'];
const DEFAULT_EXCHANGE = 'binance';

const MarketData: React.FC = () => {
  const { t } = useTranslation();
  const resolvedTheme = useAppStore((s) => s.resolvedTheme);

  const [symbol, setSymbol] = useState(SYMBOLS[0]);
  const [timeframe, setTimeframe] = useState('1h');
  const [tickers, setTickers] = useState<MarketTicker[]>([]);
  const [tickersLoading, setTickersLoading] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  // Load tickers
  useEffect(() => {
    const fetchTickers = async () => {
      setTickersLoading(true);
      try {
        const data = await marketApi.getTickers(DEFAULT_EXCHANGE, SYMBOLS);
        setTickers(data);
      } catch {
        // tickers remain empty
      } finally {
        setTickersLoading(false);
      }
    };
    fetchTickers();
  }, []);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const container = chartContainerRef.current;
    const theme = getChartTheme(resolvedTheme);

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 420,
      layout: {
        background: { color: theme.background },
        textColor: theme.textColor,
      },
      grid: {
        vertLines: { color: theme.gridColor },
        horzLines: { color: theme.gridColor },
      },
      crosshair: {
        vertLine: { color: theme.crosshairColor, labelBackgroundColor: theme.crosshairColor },
        horzLine: { color: theme.crosshairColor, labelBackgroundColor: theme.crosshairColor },
      },
      rightPriceScale: { borderColor: theme.gridColor },
      timeScale: { borderColor: theme.gridColor },
    });

    const series = chart.addCandlestickSeries({
      upColor: theme.upColor,
      downColor: theme.downColor,
      wickUpColor: theme.wickUpColor,
      wickDownColor: theme.wickDownColor,
      borderVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update chart theme when resolved theme changes
  useEffect(() => {
    if (!chartRef.current) return;
    const theme = getChartTheme(resolvedTheme);

    chartRef.current.applyOptions({
      layout: {
        background: { color: theme.background },
        textColor: theme.textColor,
      },
      grid: {
        vertLines: { color: theme.gridColor },
        horzLines: { color: theme.gridColor },
      },
      crosshair: {
        vertLine: { color: theme.crosshairColor, labelBackgroundColor: theme.crosshairColor },
        horzLine: { color: theme.crosshairColor, labelBackgroundColor: theme.crosshairColor },
      },
      rightPriceScale: { borderColor: theme.gridColor },
      timeScale: { borderColor: theme.gridColor },
    });

    if (seriesRef.current) {
      seriesRef.current.applyOptions({
        upColor: theme.upColor,
        downColor: theme.downColor,
        wickUpColor: theme.wickUpColor,
        wickDownColor: theme.wickDownColor,
      });
    }
  }, [resolvedTheme]);

  // Load candle data
  const loadCandles = useCallback(async (sym: string, tf: string) => {
    setChartLoading(true);
    try {
      const data = await marketApi.getCandles(DEFAULT_EXCHANGE, sym, tf);
      if (seriesRef.current) {
        const formatted = data.map((c) => ({
          time: c.time as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));
        seriesRef.current.setData(formatted);
        chartRef.current?.timeScale().fitContent();
      }
    } catch {
      // chart stays empty on error
    } finally {
      setChartLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCandles(symbol, timeframe);
  }, [symbol, timeframe, loadCandles]);

  const tickerColumns: ColumnsType<MarketTicker> = [
    {
      title: t('market.symbol'),
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: t('market.price'),
      dataIndex: 'last',
      key: 'last',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('market.change24h'),
      dataIndex: 'changePct24h',
      key: 'changePct24h',
      render: (v: number) => <PriceChange value={v} percent />,
    },
    {
      title: t('market.high24h'),
      dataIndex: 'high24h',
      key: 'high24h',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
    {
      title: t('market.low24h'),
      dataIndex: 'low24h',
      key: 'low24h',
      render: (v: number) =>
        `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        {t('market.title')}
      </Title>

      {/* Candlestick Chart */}
      <Card bordered={false} className="hoverable-card" style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 16,
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <Text strong style={{ fontSize: 16 }}>
            {t('market.kline')} — {symbol}
          </Text>
          <Space>
            <Select
              value={symbol}
              onChange={setSymbol}
              style={{ width: 140 }}
              options={SYMBOLS.map((s) => ({ label: s, value: s }))}
            />
            <Select
              value={timeframe}
              onChange={setTimeframe}
              style={{ width: 90 }}
              options={TIMEFRAMES.map((tf) => ({ label: tf, value: tf }))}
            />
          </Space>
        </div>

        <Spin spinning={chartLoading}>
          <div ref={chartContainerRef} style={{ width: '100%', height: 420 }} />
        </Spin>
      </Card>

      {/* Market Overview */}
      <Card
        title={t('dashboard.marketOverview')}
        bordered={false}
        className="hoverable-card"
      >
        <Table<MarketTicker>
          columns={tickerColumns}
          dataSource={tickers}
          rowKey="symbol"
          loading={tickersLoading}
          pagination={false}
          size="middle"
          locale={{ emptyText: t('common.noData') }}
          onRow={(record) => ({
            onClick: () => setSymbol(record.symbol),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </div>
  );
};

export default MarketData;
