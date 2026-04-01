export type ThemeMode = 'light' | 'dark' | 'auto';
export type Language = 'zh-CN' | 'en-US';

export interface User {
  id: string;
  email: string;
  username: string;
  avatar_url?: string;
  phone?: string;
  theme_mode: ThemeMode;
  language: Language;
  timezone: string;
  default_exchange: string;
  default_timeframe: string;
  two_fa_enabled: boolean;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface UserSettings {
  theme_mode: ThemeMode;
  language: Language;
  timezone: string;
  default_exchange: string;
  default_timeframe: string;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  strategy_type: string;
  parameters: Record<string, unknown>;
  is_active: boolean;
  is_running: boolean;
  exchange: string;
  symbol: string;
  timeframe: string;
  created_at: string;
  updated_at: string;
}

export interface CandlestickData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Order {
  id: string;
  strategy_id?: string;
  exchange: string;
  symbol: string;
  order_type: string;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  filled_quantity: number;
  status: string;
  created_at: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  fee: number;
  pnl: number;
  created_at: string;
}

export interface Portfolio {
  total_value_usdt: number;
  available_usdt: number;
  positions: Position[];
  daily_pnl: number;
  total_pnl: number;
}

export interface Position {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
}

export interface Alert {
  id: string;
  name: string;
  alert_type: string;
  symbol: string;
  condition: string;
  threshold: number;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
}

export interface Notification {
  id: string;
  title: string;
  content: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
}

export interface BacktestResult {
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  equity_curve: Array<{ time: string; value: number }>;
  trades: Array<{
    entry_time: string;
    exit_time: string;
    side: string;
    entry_price: number;
    exit_price: number;
    pnl: number;
    return_pct: number;
  }>;
}

export interface OperationLog {
  id: string;
  action: string;
  resource_type: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface ApiKey {
  id: string;
  exchange: string;
  label: string;
  permissions: string[];
  is_active: boolean;
  last_tested_at?: string;
  created_at: string;
}

export interface MarketTicker {
  symbol: string;
  last: number;
  change24h: number;
  changePct24h: number;
  high24h: number;
  low24h: number;
  volume24h: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
