"use client";

import React, { useEffect, useState } from "react";

import styles from "./Topbar.module.css";

type Theme = "light" | "dark";

const THEME_STORAGE_KEY = "serviceai_theme";

// определяем начальную тему (как в ui.store, но локально)
function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }

  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }

  return "light";
}

const Topbar: React.FC = () => {
  // локальное состояние вместо useUiStore
  const [theme, setTheme] = useState<Theme>(() => getInitialTheme());
  const [globalLoading] = useState(false);       // пока заглушки
  const [lastError] = useState<string | null>(null);

  // применяем тему к документу и в localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const themeLabel = theme === "dark" ? "Светлая тема" : "Темная тема";

  return (
    <header className={styles.topbar}>
      <div className={styles.title}>Панель управления</div>
      <div className={styles.actions}>
        <div className={styles.statuses}>
          {globalLoading && (
            <span className={`${styles.status} ${styles.loading}`}>
              Загрузка
            </span>
          )}
          {lastError && (
            <span className={`${styles.status} ${styles.error}`}>
              {lastError}
            </span>
          )}
        </div>
        <button
          type="button"
          className={styles.themeToggle}
          onClick={toggleTheme}
        >
          {themeLabel}
        </button>
        <div className={styles.avatar}>АК</div>
      </div>
    </header>
  );
};

export default Topbar;
