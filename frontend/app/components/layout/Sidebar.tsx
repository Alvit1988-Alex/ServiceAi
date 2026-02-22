"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";

import styles from "./Sidebar.module.css";

const navItems = [
  { label: "Дашборд", href: "/" },
  { label: "Боты", href: "/bots" },
  { label: "Поиск", href: "/search" },
  { label: "Интеграции", href: "/integrations" },
  { label: "Настройки", href: "/settings" },
];

export function Sidebar() {
  // локальный стейт сворачивания вместо zustand
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const pathname = usePathname();

  const className = [styles.sidebar, sidebarCollapsed ? styles.collapsed : ""]
    .filter(Boolean)
    .join(" ");

  const handleToggle = () => {
    setSidebarCollapsed((prev) => !prev);
  };

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
          onClick={handleToggle}
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
            const isActive = pathname === item.href;
            const linkClassName = [styles.navLink, isActive ? styles.active : ""]
              .filter(Boolean)
              .join(" ");

            return (
              <li key={item.label} className={styles.navItem}>
                <Link
                  href={item.href}
                  className={linkClassName}
                  aria-current={isActive ? "page" : undefined}
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
