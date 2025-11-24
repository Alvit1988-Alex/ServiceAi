import LayoutShell from "./components/layout/LayoutShell";
import styles from "./page.module.css";
import { AuthGuard } from "./components/auth/AuthGuard";

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
    <AuthGuard>
      <LayoutShell
        title="Панель управления ServiceAI"
        description="Краткое описание состояния сервисов и полезные показатели. Обновления происходят в реальном времени, чтобы вы могли быстро реагировать на ключевые изменения."
      >
        <section className={styles.loginSection}>
          <div className={styles.loginHeader}>
            <h2 className={styles.loginTitle}>Сводка по сервисам</h2>
            <p className={styles.loginDescription}>
              Добро пожаловать! Используйте сводку ниже, чтобы оперативно оценить
              состояние системы и перейти к нужным разделам.
            </p>
          </div>
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
    </AuthGuard>
  );
}
