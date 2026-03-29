"use client";

import { create } from "zustand";

import {
  completeYandexLogin as completeYandexLoginApi,
  getCurrentUser,
  login as loginApi,
  refreshToken as refreshTokenApi,
} from "@/app/api/authApi";
import { updateAccountProfile } from "@/app/api/accountApi";
import { AuthTokens, User } from "@/app/api/types";

export const AUTH_STORAGE_KEY = "serviceai_auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  profileCompletionRequired: boolean;
  isAuthenticated: boolean;
  isInitialized: boolean;
  loading: boolean;
  error: string | null;

  setTokens: (accessToken: string, refreshToken: string) => void;
  login: (email: string, password: string) => Promise<void>;
  completeYandexLogin: (completionToken: string) => Promise<void>;
  completeProfile: (firstName: string, lastName: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
  initFromStorage: () => Promise<void>;
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

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  profileCompletionRequired: false,
  isAuthenticated: false,
  isInitialized: false,
  loading: false,
  error: null,

  setTokens: (accessToken: string, refreshToken: string) => {
    set({ accessToken, refreshToken });
    persistTokens({ access_token: accessToken, refresh_token: refreshToken });
  },

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });

    try {
      const tokens = await loginApi(email, password);
      get().setTokens(tokens.access_token!, tokens.refresh_token!);

      const user = await getCurrentUser(tokens.access_token!);

      set({
        user,
        loading: false,
        isAuthenticated: true,
        isInitialized: true,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Login failed";

      set({
        error: message,
        loading: false,
        isAuthenticated: false,
        isInitialized: true,
      });

      throw error;
    }
  },

  completeYandexLogin: async (completionToken: string) => {
    set({ loading: true, error: null });

    try {
      const tokens = await completeYandexLoginApi(completionToken);
      if (!tokens.access_token || !tokens.refresh_token) {
        throw new Error("Не удалось получить токены после входа через Яндекс");
      }

      get().setTokens(tokens.access_token, tokens.refresh_token);
      const user = await getCurrentUser(tokens.access_token);

      set({
        user,
        loading: false,
        profileCompletionRequired: tokens.requires_profile_completion ?? false,
        isAuthenticated: true,
        isInitialized: true,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось завершить вход";

      set({
        error: message,
        loading: false,
        isAuthenticated: false,
        isInitialized: true,
      });

      throw error;
    }
  },

  completeProfile: async (firstName: string, lastName: string) => {
    const user = get().user;
    if (!user?.id) {
      set({ error: "Нет данных пользователя" });
      return;
    }
    const updated = await updateAccountProfile(user.id, {
      first_name: firstName,
      last_name: lastName,
      email: user.email,
    });
    set({ user: updated, profileCompletionRequired: false, isAuthenticated: true });
  },

  logout: () => {
    persistTokens(null);
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      profileCompletionRequired: false,
      isAuthenticated: false,
      loading: false,
      error: null,
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
      get().setTokens(tokens.access_token!, tokens.refresh_token!);
    } catch (error) {
      console.error("Failed to refresh session", error);
      get().logout();
    }
  },

  initFromStorage: async () => {
    if (get().isInitialized) return;

    const tokens = loadTokens();

    if (!tokens?.access_token || !tokens?.refresh_token) {
      set({
        isInitialized: true,
        isAuthenticated: false,
        user: null,
        accessToken: null,
        refreshToken: null,
      });
      return;
    }

    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    });

    try {
      const user = await getCurrentUser(tokens.access_token);

      set({
        user,
        profileCompletionRequired: false,
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
}));
