import apiClient from './client';
import type { Strategy } from '../types';

export interface CreateStrategyRequest {
  name: string;
  description?: string;
  strategy_type: string;
  parameters: Record<string, unknown>;
  exchange: string;
  symbol: string;
  timeframe: string;
}

export const strategiesApi = {
  list: (page = 1, pageSize = 20) =>
    apiClient.get<{ items: Strategy[]; total: number }>('/strategies', { params: { page, page_size: pageSize } }).then(r => r.data),
  get: (id: string) =>
    apiClient.get<Strategy>(`/strategies/${id}`).then(r => r.data),
  create: (data: CreateStrategyRequest) =>
    apiClient.post<Strategy>('/strategies', data).then(r => r.data),
  update: (id: string, data: Partial<CreateStrategyRequest>) =>
    apiClient.put<Strategy>(`/strategies/${id}`, data).then(r => r.data),
  delete: (id: string) =>
    apiClient.delete(`/strategies/${id}`).then(r => r.data),
  start: (id: string) =>
    apiClient.post(`/strategies/${id}/start`).then(r => r.data),
  stop: (id: string) =>
    apiClient.post(`/strategies/${id}/stop`).then(r => r.data),
  getBacktestResults: (id: string) =>
    apiClient.get(`/strategies/${id}/backtest`).then(r => r.data),
  runBacktest: (id: string, params: { start_date: string; end_date: string; initial_capital: number; commission?: number; slippage?: number }) =>
    apiClient.post(`/strategies/${id}/backtest`, params).then(r => r.data),
};
