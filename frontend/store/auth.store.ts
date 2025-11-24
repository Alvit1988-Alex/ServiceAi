"use client";

import { create } from "zustand";

import { getCurrentUser, login as loginApi, refreshToken as refreshTokenApi } from "@/app/api/authApi";
import { AuthTokens, User } from "@/app/api/types";

export const AUTH_STORAGE_KEY = "serviceai_auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
  loading: boolean;
  error: string | null;
  setTokens: (accessToken: string, refreshToken: string) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
  initFromStorage: () => Promise<void>;
}

function persistTokens(tokens: AuthTokens | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (!tokens) {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
}

function loadTokens(): AuthTokens | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

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
  isAuthenticated: false,
  isInitialized: false,
  loading: false,
  error: null,
  setTokens: (accessToken: string, refreshToken: string) => {
    set({ accessToken, refreshToken, isAuthenticated: true });
    persistTokens({ access_token: accessToken, refresh_token: refreshToken });
  },
  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const tokens = await loginApi(email, password);
      get().setTokens(tokens.access_token, tokens.refresh_token);
      const user = await getCurrentUser(tokens.access_token);
      set({ user, loading: false, isAuthenticated: true });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Login failed";
      set({ error: message, loading: false, isAuthenticated: false });
      throw error;
    }
  },
  logout: () => {
    persistTokens(null);
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
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
      get().setTokens(tokens.access_token, tokens.refresh_token);
    } catch (error) {
      console.error("Failed to refresh session", error);
      get().logout();
    }
  },
  initFromStorage: async () => {
    if (get().isInitialized) {
      return;
    }

    const tokens = loadTokens();

    if (!tokens) {
      set({ isInitialized: true });
      return;
    }

    get().setTokens(tokens.access_token, tokens.refresh_token);

    try {
      const user = await getCurrentUser(tokens.access_token);
      set({ user, isInitialized: true, isAuthenticated: true });
    } catch (error) {
      console.error("Failed to load user during init", error);
      get().logout();
      set({ isInitialized: true });
    }
  },
}));
