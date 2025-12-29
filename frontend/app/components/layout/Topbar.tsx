"use client";

import React from "react";

import { useUiStore } from "../../../store/ui.store";
import styles from "./Topbar.module.css";

const Topbar: React.FC = () => {
  const theme = useUiStore((state) => state.theme);
  const toggleTheme = useUiStore((state) => state.toggleTheme);
  const globalLoading = useUiStore((state) => state.globalLoading);
  const lastError = useUiStore((state) => state.lastError);

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
