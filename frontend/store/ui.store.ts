"use client";

import { create } from "zustand";

type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "serviceai_theme";
const SIDEBAR_STORAGE_KEY = "serviceai_sidebar_collapsed";

function getSystemTheme(): Theme {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function readThemeFromStorage(): Theme {
  if (typeof window === "undefined") {
    return "light";
  }

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }

  const htmlTheme = document.documentElement.getAttribute("data-theme");
  if (htmlTheme === "light" || htmlTheme === "dark") {
    return htmlTheme;
  }

  return getSystemTheme();
}

function applyTheme(theme: Theme) {
  if (typeof window === "undefined") {
    return;
  }

  document.documentElement.setAttribute("data-theme", theme);
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
}

function readSidebarFromStorage(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
}

function persistSidebar(collapsed: boolean) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(collapsed));
}

interface UiState {
  theme: Theme;
  sidebarCollapsed: boolean;
  globalLoading: boolean;
  lastError: string | null;
  initialized: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  setGlobalLoading: (value: boolean) => void;
  setLastError: (message: string | null) => void;
  initUi: () => void;
}

export const useUiStore = create<UiState>((set, get) => ({
  theme: typeof window !== "undefined" ? readThemeFromStorage() : "light",
  sidebarCollapsed:
    typeof window !== "undefined" ? readSidebarFromStorage() : false,
  globalLoading: false,
  lastError: null,
  initialized: false,
  setTheme: (theme: Theme) => {
    set({ theme });
    applyTheme(theme);
  },
  toggleTheme: () => {
    const nextTheme = get().theme === "light" ? "dark" : "light";
    get().setTheme(nextTheme);
  },
  setSidebarCollapsed: (collapsed: boolean) => {
    set({ sidebarCollapsed: collapsed });
    persistSidebar(collapsed);
  },
  toggleSidebar: () => {
    const nextState = !get().sidebarCollapsed;
    get().setSidebarCollapsed(nextState);
  },
  setGlobalLoading: (value: boolean) => set({ globalLoading: value }),
  setLastError: (message: string | null) => set({ lastError: message }),
  initUi: () => {
    if (get().initialized) {
      return;
    }

    const theme = readThemeFromStorage();
    const sidebarCollapsed = readSidebarFromStorage();

    set({ theme, sidebarCollapsed, initialized: true });
    applyTheme(theme);
    persistSidebar(sidebarCollapsed);
  },
}));
