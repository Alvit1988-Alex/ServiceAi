"use client";

import Link from "next/link";

import { useUiStore } from "@/store/ui.store";

import styles from "./Sidebar.module.css";

const navItems = [
  { label: "Дашборд", href: "#", active: true },
  { label: "Боты", href: "#" },
  { label: "Диалоги", href: "#" },
  { label: "AI-настройки", href: "#" },
  { label: "База знаний", href: "#" },
  { label: "Поиск", href: "#" },
  { label: "Настройки", href: "#" },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUiStore((state) => ({
    sidebarCollapsed: state.sidebarCollapsed,
    toggleSidebar: state.toggleSidebar,
  }));

  const className = [styles.sidebar, sidebarCollapsed ? styles.collapsed : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <aside className={className} aria-label="Основная навигация">
      <div className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoAccent}>Service</span>
          <span className={styles.logoText}>AI</span>
        </div>

        <button
          type="button"
          className={styles.toggle}
          aria-label="Переключить размер меню"
          onClick={toggleSidebar}
        >
          <span aria-hidden>{sidebarCollapsed ? ">" : "<"}</span>
          <span className={styles.toggleLabel}>
            {sidebarCollapsed ? "Развернуть" : "Свернуть"}
          </span>
        </button>
      </div>

      <nav className={styles.nav}>
        <ul className={styles.navList}>
          {navItems.map((item) => {
            const linkClassName = [
              styles.navLink,
              item.active ? styles.active : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <li key={item.label} className={styles.navItem}>
                <Link
                  href={item.href}
                  className={linkClassName}
                  aria-current={item.active ? "page" : undefined}
                >
                  <span className={styles.navDot} aria-hidden>
                    •
                  </span>
                  <span className={styles.navLabel}>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
