import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { getChartTheme } from '../../themes';
import { useAppStore } from '../../store';

interface PortfolioChartProps {
  data: Array<{ time: string; value: number }>;
  height?: number;
}

const PortfolioChart: React.FC<PortfolioChartProps> = ({ data, height = 300 }) => {
  const resolvedTheme = useAppStore((s) => s.resolvedTheme);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const theme = getChartTheme(resolvedTheme);
    const lineColor = '#1668dc';

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

    const series = chart.addLineSeries({
      color: lineColor,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
    });

    // Area fill below line
    chart.addAreaSeries({
      topColor: 'rgba(22, 104, 220, 0.28)',
      bottomColor: 'rgba(22, 104, 220, 0.02)',
      lineColor: 'transparent',
      lineWidth: 1,
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

  // Update theme
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
  }, [resolvedTheme]);

  // Update data
  useEffect(() => {
    if (!seriesRef.current || !data.length) return;

    const formatted = data.map((d) => ({
      time: d.time as unknown as UTCTimestamp,
      value: d.value,
    }));

    seriesRef.current.setData(formatted);
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
};

export default PortfolioChart;
