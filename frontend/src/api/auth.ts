import apiClient from './client';

export interface LoginRequest { email: string; password: string; }
export interface RegisterRequest { email: string; username: string; password: string; }
export interface AuthResponse { access_token: string; refresh_token: string; token_type: string; }

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<AuthResponse>('/auth/login', data).then(r => r.data),
  register: (data: RegisterRequest) =>
    apiClient.post<AuthResponse>('/auth/register', data).then(r => r.data),
  refreshToken: (refresh_token: string) =>
    apiClient.post<AuthResponse>('/auth/refresh', { refresh_token }).then(r => r.data),
  logout: () =>
    apiClient.post('/auth/logout').then(r => r.data),
  me: () =>
    apiClient.get('/auth/me').then(r => r.data),
};
