import apiClient from './client';
import type { Order, Trade, Portfolio } from '../types';

export const tradingApi = {
  getPortfolio: (exchange?: string) =>
    apiClient.get<Portfolio>('/portfolio', { params: { exchange } }).then((r) => r.data),

  getPositions: (exchange?: string) =>
    apiClient.get('/portfolio/positions', { params: { exchange } }).then((r) => r.data),

  getPnlHistory: (days = 30) =>
    apiClient.get('/portfolio/pnl-history', { params: { days } }).then((r) => r.data),

  placeOrder: (data: {
    exchange: string;
    symbol: string;
    side: 'buy' | 'sell';
    order_type: 'market' | 'limit';
    quantity: number;
    price?: number;
    strategy_id?: string;
  }) => apiClient.post<Order>('/trading/orders', data).then((r) => r.data),

  cancelOrder: (orderId: string) =>
    apiClient.delete(`/trading/orders/${orderId}`).then((r) => r.data),

  getOrders: (params?: { status?: string; symbol?: string; page?: number; page_size?: number }) =>
    apiClient.get<{ items: Order[]; total: number }>('/trading/orders', { params }).then((r) => r.data),

  getTrades: (params?: { symbol?: string; page?: number; page_size?: number }) =>
    apiClient.get<{ items: Trade[]; total: number }>('/trading/trades', { params }).then((r) => r.data),

  getTradeStats: () =>
    apiClient.get('/trading/trades/stats').then((r) => r.data),
};
