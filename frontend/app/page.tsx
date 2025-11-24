import LayoutShell from "./components/layout/LayoutShell";
import styles from "./page.module.css";
import { Button } from "./components/Button/Button";

const stats = [
  {
    label: "Активные сервисы",
    value: "12",
    note: "работают без сбоев",
  },
  {
    label: "Среднее время ответа",
    value: "180 мс",
    note: "за последние 24 часа",
  },
  {
    label: "Запросов за сутки",
    value: "1,2 млн",
    note: "+4% к прошлому дню",
  },
];

export default function Home() {
  return (
    <LayoutShell
      title="Панель управления ServiceAI"
      description="Краткое описание состояния сервисов и полезные показатели. Обновления происходят в реальном времени, чтобы вы могли быстро реагировать на ключевые изменения."
    >
      <section className={styles.loginSection}>
        <div className={styles.loginHeader}>
          <h2 className={styles.loginTitle}>Вход в панель управления</h2>
          <p className={styles.loginDescription}>
            Используйте корпоративную почту или логин, чтобы получить доступ к
            аналитике и настройкам сервисов.
          </p>
        </div>

        <form className={styles.loginForm}>
          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel} htmlFor="login">
              Email или логин
            </label>
            <input
              className={styles.fieldInput}
              id="login"
              name="login"
              type="text"
              autoComplete="username"
              placeholder="name@company.com"
            />
          </div>

          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel} htmlFor="password">
              Пароль
            </label>
            <input
              className={styles.fieldInput}
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </div>

          <div className={styles.actions}>
            <Button type="submit">Войти</Button>
          </div>
        </form>
      </section>

      {stats.length > 0 && (
        <div className={styles.cards} aria-label="Ключевые показатели">
          {stats.map((stat) => (
            <article key={stat.label} className={styles.card}>
              <p className={styles.cardLabel}>{stat.label}</p>
              <p className={styles.cardValue}>{stat.value}</p>
              <p className={styles.cardNote}>{stat.note}</p>
            </article>
          ))}
        </div>
      )}
    </LayoutShell>
  );
}
