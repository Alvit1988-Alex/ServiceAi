"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./AppTabs.module.css";

const tabs = [
  { label: "Дашборд", href: "/" },
  { label: "Каналы", href: "/channels" },
  { label: "ИИ и база знаний", href: "/knowledge" },
  { label: "Диалоги", href: "/search" },
  { label: "Настройки", href: "/settings" },
];

const isActivePath = (pathname: string, href: string) => {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
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
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
