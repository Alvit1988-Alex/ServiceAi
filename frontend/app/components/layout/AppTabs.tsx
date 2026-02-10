"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./AppTabs.module.css";

type TabIconName = "dashboard" | "channels" | "training" | "dialogs" | "settings";

const tabs: Array<{ label: string; href: string; icon: TabIconName }> = [
  { label: "Дашборд", href: "/", icon: "dashboard" },
  { label: "Каналы", href: "/channels", icon: "channels" },
  { label: "Обучение ИИ", href: "/knowledge", icon: "training" },
  { label: "Диалоги", href: "/search", icon: "dialogs" },
  { label: "Настройки", href: "/settings", icon: "settings" },
];

const isActivePath = (pathname: string, href: string) => {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
};

const renderIcon = (name: TabIconName) => {
  switch (name) {
    case "dashboard":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 10.5 12 3l9 7.5" />
          <path d="M5 9.5V21h14V9.5" />
          <path d="M9 21v-6h6v6" />
        </svg>
      );
    case "channels":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 6.5h16v10H8l-4 3V6.5Z" />
          <path d="M8 10h8" />
          <path d="M8 13h5" />
        </svg>
      );
    case "training":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4.5 5.5h6.5a3 3 0 0 1 3 3V20a3 3 0 0 0-3-3H4.5v-11.5Z" />
          <path d="M19.5 5.5H13a3 3 0 0 0-3 3V20a3 3 0 0 1 3-3h6.5v-11.5Z" />
          <path d="M10 9.5h4" />
        </svg>
      );
    case "dialogs":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="6.5" />
          <path d="m16 16 4 4" />
          <path d="M8.5 11h5" />
        </svg>
      );
    case "settings":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3.2" />
          <path d="M12 3v2.2" />
          <path d="M12 18.8V21" />
          <path d="m4.9 4.9 1.6 1.6" />
          <path d="m17.5 17.5 1.6 1.6" />
          <path d="M3 12h2.2" />
          <path d="M18.8 12H21" />
          <path d="m4.9 19.1 1.6-1.6" />
          <path d="m17.5 6.5 1.6-1.6" />
        </svg>
      );
    default:
      return null;
  }
};

export default function AppTabs() {
  const pathname = usePathname();

  return (
    <nav className={styles.tabs} aria-label="Основная навигация">
      {tabs.map((tab) => {
        const active = isActivePath(pathname, tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`${styles.tab} ${active ? styles.tabActive : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <span className={styles.tabLabel}>{tab.label}</span>
            <span className={styles.tabIcon} aria-hidden="true">
              {renderIcon(tab.icon)}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
