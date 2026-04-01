import apiClient from './client';
import type { Alert } from '../types';

export const alertsApi = {
  getAlerts: (params?: { page?: number; page_size?: number }) =>
    apiClient
      .get<{ items: Alert[]; total: number }>('/alerts', { params })
      .then((r) => r.data),

  getAlert: (id: string) =>
    apiClient.get<Alert>(`/alerts/${id}`).then((r) => r.data),

  createAlert: (data: {
    name: string;
    alert_type: string;
    exchange: string;
    symbol: string;
    condition: string;
    threshold: number;
  }) => apiClient.post<Alert>('/alerts', data).then((r) => r.data),

  updateAlert: (
    id: string,
    data: Partial<{
      name: string;
      alert_type: string;
      exchange: string;
      symbol: string;
      condition: string;
      threshold: number;
      is_active: boolean;
    }>
  ) => apiClient.put<Alert>(`/alerts/${id}`, data).then((r) => r.data),

  deleteAlert: (id: string) =>
    apiClient.delete(`/alerts/${id}`).then((r) => r.data),

  toggleAlert: (id: string, is_active: boolean) =>
    apiClient.put<Alert>(`/alerts/${id}`, { is_active }).then((r) => r.data),
};
