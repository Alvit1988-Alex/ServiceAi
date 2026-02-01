"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useUiStore } from "../../../store/ui.store";
import { useAuthStore } from "../../../store/auth.store";
import styles from "./Topbar.module.css";

const Topbar: React.FC = () => {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const theme = useUiStore((state) => state.theme);
  const toggleTheme = useUiStore((state) => state.toggleTheme);
  const globalLoading = useUiStore((state) => state.globalLoading);
  const lastError = useUiStore((state) => state.lastError);

  const themeLabel = theme === "dark" ? "Светлая тема" : "Темная тема";
  const isActive = (path: string) => {
    if (path === "/") return pathname === "/";
    return pathname === path || pathname.startsWith(`${path}/`);
  };

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <div className={styles.brand} aria-label="Service AI">
          <span className={styles.brandAccent}>Service</span>
          <span className={styles.brandText}>AI</span>
        </div>
        <nav className={styles.tabs} aria-label="Навигация">
          <Link className={`${styles.tab} ${isActive("/") ? styles.tabActive : ""}`} href="/">
            Дашборд
          </Link>
          <Link
            className={`${styles.tab} ${isActive("/channels") ? styles.tabActive : ""}`}
            href="/channels"
          >
            Каналы
          </Link>
          <Link
            className={`${styles.tab} ${isActive("/knowledge") ? styles.tabActive : ""}`}
            href="/knowledge"
          >
            ИИ и база знаний
          </Link>
          <Link
            className={`${styles.tab} ${isActive("/search") ? styles.tabActive : ""}`}
            href="/search"
          >
            Диалоги
          </Link>
          <Link
            className={`${styles.tab} ${isActive("/settings") ? styles.tabActive : ""}`}
            href="/settings"
          >
            Настройки
          </Link>
        </nav>
      </div>
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
        <button
          className={styles.logout}
          type="button"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
        >
          Выход
        </button>
        <div className={styles.avatar}>АК</div>
      </div>
    </header>
  );
};

export default Topbar;
