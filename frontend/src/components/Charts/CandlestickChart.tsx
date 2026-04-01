import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { getChartTheme } from '../../themes';
import { useAppStore } from '../../store';
import type { CandlestickData } from '../../types';

interface CandlestickChartProps {
  data: CandlestickData[];
  height?: number;
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({ data, height = 400 }) => {
  const resolvedTheme = useAppStore((s) => s.resolvedTheme);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const theme = getChartTheme(resolvedTheme);

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
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
  }, [height]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update theme when resolvedTheme changes
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

  // Update data
  useEffect(() => {
    if (!seriesRef.current || !data.length) return;

    const formatted = data.map((c) => ({
      time: c.time as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    seriesRef.current.setData(formatted);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
};

export default CandlestickChart;
