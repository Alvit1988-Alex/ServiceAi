import styles from "./page.module.css";

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
    <section className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Панель управления ServiceAI</h1>
        <p className={styles.description}>
          Краткое описание состояния сервисов и полезные показатели. Обновления
          происходят в реальном времени, чтобы вы могли быстро реагировать на
          ключевые изменения.
        </p>
      </header>

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
    </section>
  );
}
