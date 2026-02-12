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
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 10.5 12 3l9 7.5" />
          <path d="M5 10v11h14V10" />
          <path d="M9 21v-6h6v6" />
        </svg>
      );
    case "channels":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 6h16v10H8l-4 4V6Z" />
          <path d="M8 10h8" />
          <path d="M8 13h6" />
        </svg>
      );
    case "training":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 5h6a3 3 0 0 1 3 3v11a3 3 0 0 0-3-3H4V5Z" />
          <path d="M20 5h-6a3 3 0 0 0-3 3v11a3 3 0 0 1 3-3h6V5Z" />
        </svg>
      );
    case "dialogs":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="6" />
          <path d="m20 20-4.2-4.2" />
        </svg>
      );
    case "settings":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z" />
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
