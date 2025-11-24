import Link from "next/link";
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
  return (
    <aside className={styles.sidebar} aria-label="Основная навигация">
      <div className={styles.logo}>
        <span className={styles.logoAccent}>Service</span>
        <span className={styles.logoText}>AI</span>
      </div>

      <nav className={styles.nav}>
        <ul className={styles.navList}>
          {navItems.map((item) => {
            const className = [
              styles.navLink,
              item.active ? styles.active : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <li key={item.label} className={styles.navItem}>
                <Link
                  href={item.href}
                  className={className}
                  aria-current={item.active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
