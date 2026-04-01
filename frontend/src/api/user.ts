import apiClient from './client';
import type { User, UserSettings } from '../types';

export const userApi = {
  getProfile: () =>
    apiClient.get<User>('/users/me').then(r => r.data),
  updateProfile: (data: Partial<User>) =>
    apiClient.put<User>('/users/me', data).then(r => r.data),
  updateSettings: (data: Partial<UserSettings>) =>
    apiClient.put<UserSettings>('/users/me/settings', data).then(r => r.data),
  changePassword: (current_password: string, new_password: string) =>
    apiClient.post('/users/me/change-password', { current_password, new_password }).then(r => r.data),
  getApiKeys: () =>
    apiClient.get('/users/me/api-keys').then(r => r.data),
  createApiKey: (data: { exchange: string; label: string; api_key: string; api_secret: string; permissions: string[] }) =>
    apiClient.post('/users/me/api-keys', data).then(r => r.data),
  deleteApiKey: (id: string) =>
    apiClient.delete(`/users/me/api-keys/${id}`).then(r => r.data),
  testApiKey: (id: string) =>
    apiClient.post(`/users/me/api-keys/${id}/test`).then(r => r.data),
  getNotifications: (page = 1, pageSize = 20) =>
    apiClient.get('/users/me/notifications', { params: { page, page_size: pageSize } }).then(r => r.data),
  markNotificationRead: (id: string) =>
    apiClient.put(`/users/me/notifications/${id}/read`).then(r => r.data),
  markAllNotificationsRead: () =>
    apiClient.put('/users/me/notifications/read-all').then(r => r.data),
  getOperationLog: (page = 1, pageSize = 20) =>
    apiClient.get('/users/me/operation-log', { params: { page, page_size: pageSize } }).then(r => r.data),
  getSessions: () =>
    apiClient.get('/users/me/sessions').then(r => r.data),
  revokeSession: (id: string) =>
    apiClient.delete(`/users/me/sessions/${id}`).then(r => r.data),
  enable2FA: () =>
    apiClient.post('/users/me/2fa/enable').then(r => r.data),
  disable2FA: (code: string) =>
    apiClient.post('/users/me/2fa/disable', { code }).then(r => r.data),
  verify2FA: (code: string) =>
    apiClient.post('/users/me/2fa/verify', { code }).then(r => r.data),
};
