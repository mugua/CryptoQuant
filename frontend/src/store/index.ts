import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, ThemeMode, Language } from '../types';

interface AppStore {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;

  themeMode: ThemeMode;
  resolvedTheme: 'light' | 'dark';
  setThemeMode: (mode: ThemeMode) => void;
  setResolvedTheme: (theme: 'light' | 'dark') => void;

  language: Language;
  setLanguage: (lang: Language) => void;

  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;

  unreadCount: number;
  setUnreadCount: (n: number) => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      user: null,
      accessToken: localStorage.getItem('cryptoquant-access-token'),
      refreshToken: localStorage.getItem('cryptoquant-refresh-token'),
      isAuthenticated: !!localStorage.getItem('cryptoquant-access-token'),
      setUser: (user) => set({ user }),
      setTokens: (accessToken, refreshToken) => {
        localStorage.setItem('cryptoquant-access-token', accessToken);
        localStorage.setItem('cryptoquant-refresh-token', refreshToken);
        set({ accessToken, refreshToken, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem('cryptoquant-access-token');
        localStorage.removeItem('cryptoquant-refresh-token');
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },

      themeMode: 'auto',
      resolvedTheme: 'dark',
      setThemeMode: (themeMode) => set({ themeMode }),
      setResolvedTheme: (resolvedTheme) => set({ resolvedTheme }),

      language: 'zh-CN',
      setLanguage: (language) => set({ language }),

      sidebarCollapsed: false,
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),

      unreadCount: 0,
      setUnreadCount: (unreadCount) => set({ unreadCount }),
    }),
    {
      name: 'cryptoquant-store',
      partialize: (state) => ({
        themeMode: state.themeMode,
        language: state.language,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
