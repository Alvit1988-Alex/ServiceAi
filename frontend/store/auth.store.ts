"use client";

import { create } from "zustand";

import {
  getCurrentUser,
  login as loginApi,
  refreshToken as refreshTokenApi,
  createPendingLogin,
  getPendingStatus,
} from "@/app/api/authApi";
import { AuthTokens, PendingLoginStatus, User } from "@/app/api/types";

export const AUTH_STORAGE_KEY = "serviceai_auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
  loading: boolean;
  error: string | null;
  pendingToken: string | null;
  pendingExpiresAt: string | null;
  pendingStatus: PendingLoginStatus | null;
  pendingDeeplink: string | null;
  polling: boolean;

  setTokens: (accessToken: string, refreshToken: string) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
  initFromStorage: () => Promise<void>;
  startTelegramLogin: () => Promise<void>;
  pollPendingLogin: () => Promise<void>;
}

function persistTokens(tokens: AuthTokens | null) {
  if (typeof window === "undefined") return;

  if (!tokens) {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
}

function loadTokens(): AuthTokens | null {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as AuthTokens;
  } catch (error) {
    console.error("Failed to parse stored tokens", error);
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

let pollTimeout: ReturnType<typeof setTimeout> | null = null;

function schedulePoll(callback: () => void, delay = 1500) {
  if (pollTimeout) {
    clearTimeout(pollTimeout);
  }
  pollTimeout = setTimeout(callback, delay);
}

function clearPoll() {
  if (pollTimeout) {
    clearTimeout(pollTimeout);
    pollTimeout = null;
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isInitialized: false,
  loading: false,
  error: null,
  pendingToken: null,
  pendingExpiresAt: null,
  pendingStatus: null,
  pendingDeeplink: null,
  polling: false,

  // Просто сохраняем токены + в localStorage,
  // флаг isAuthenticated выставляем в login / initFromStorage.
  setTokens: (accessToken: string, refreshToken: string) => {
    set({ accessToken, refreshToken });
    persistTokens({ access_token: accessToken, refresh_token: refreshToken });
  },

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });

    try {
      const tokens = await loginApi(email, password);
      get().setTokens(tokens.access_token, tokens.refresh_token);

      const user = await getCurrentUser(tokens.access_token);

      set({
        user,
        loading: false,
        isAuthenticated: true,
        isInitialized: true,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Login failed";

      set({
        error: message,
        loading: false,
        isAuthenticated: false,
        // инициализация всё равно закончилась
        isInitialized: true,
      });

      throw error;
    }
  },

  logout: () => {
    clearPoll();
    persistTokens(null);
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      loading: false,
      error: null,
      pendingToken: null,
      pendingExpiresAt: null,
      pendingStatus: null,
      pendingDeeplink: null,
      polling: false,
      // флаг инициализации не трогаем — приложение уже “знает” своё состояние
    });
  },

  refreshSession: async () => {
    const refreshToken = get().refreshToken;
    if (!refreshToken) {
      get().logout();
      return;
    }

    try {
      const tokens = await refreshTokenApi(refreshToken);
      get().setTokens(tokens.access_token, tokens.refresh_token);
    } catch (error) {
      console.error("Failed to refresh session", error);
      get().logout();
    }
  },

  initFromStorage: async () => {
    // Если уже инициализированы — ничего не делаем
    if (get().isInitialized) return;

    const tokens = loadTokens();

    // Если токенов нет — просто считаем, что инициализация завершена
    if (!tokens) {
      set({
        isInitialized: true,
        isAuthenticated: false,
        user: null,
        accessToken: null,
        refreshToken: null,
      });
      return;
    }

    // Проставляем токены, но пока не отмечаем пользователя как авторизованного,
    // пока не проверим их на бэке
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });

    try {
      const user = await getCurrentUser(tokens.access_token);

      set({
        user,
        isAuthenticated: true,
        isInitialized: true,
      });
    } catch (error) {
      console.error("Failed to load user during init", error);
      persistTokens(null);
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isInitialized: true,
      });
    }
  },

  startTelegramLogin: async () => {
    set({ loading: true, error: null });
    clearPoll();
    try {
      const pending = await createPendingLogin();
      set({
        pendingToken: pending.token,
        pendingExpiresAt: pending.expires_at,
        pendingStatus: pending.status,
        pendingDeeplink: pending.telegram_deeplink,
        polling: true,
        loading: false,
      });
      schedulePoll(() => void get().pollPendingLogin());
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось подготовить вход";
      set({
        error: message,
        loading: false,
        polling: false,
      });
      throw error;
    }
  },

  pollPendingLogin: async () => {
    const token = get().pendingToken;
    if (!token) {
      clearPoll();
      return;
    }

    try {
      const status = await getPendingStatus(token);
      set({
        pendingStatus: status.status,
        pendingExpiresAt: status.expires_at,
      });

      if (status.status === "confirmed" && status.access_token && status.refresh_token) {
        get().setTokens(status.access_token, status.refresh_token);
        const user = await getCurrentUser(status.access_token);
        set({
          user,
          isAuthenticated: true,
          isInitialized: true,
          loading: false,
          polling: false,
        });
        clearPoll();
        return;
      }

      if (status.status === "expired") {
        await get().startTelegramLogin();
        return;
      }

      schedulePoll(() => void get().pollPendingLogin());
    } catch (error) {
      console.error("Failed to poll pending login", error);
      set({
        error: error instanceof Error ? error.message : "Не удалось обновить статус входа",
        polling: false,
        loading: false,
      });
      clearPoll();
    }
  },
}));
