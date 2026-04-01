import React from 'react';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface PriceChangeProps {
  value: number;
  percent?: boolean;
  showIcon?: boolean;
}

const PriceChange: React.FC<PriceChangeProps> = ({ value, percent = false, showIcon = true }) => {
  const isPositive = value > 0;
  const isNegative = value < 0;

  const color = isPositive ? '#26a69a' : isNegative ? '#ef5350' : undefined;

  const formatted = `${isPositive ? '+' : ''}${
    percent ? `${value.toFixed(2)}%` : value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }`;

  return (
    <span style={{ color, fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      {showIcon && isPositive && <ArrowUpOutlined />}
      {showIcon && isNegative && <ArrowDownOutlined />}
      {formatted}
    </span>
  );
};

export default PriceChange;
