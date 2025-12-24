"use client";

import { BotDTO } from "@/store/bots.store";

import styles from "./BotOverview.module.css";

interface BotOverviewProps {
  bot: BotDTO;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function BotOverview({ bot }: BotOverviewProps) {
  const accountIdValue =
    typeof bot.account_id === "number" ? `#${bot.account_id}` : "—";
  const createdAtValue =
    typeof bot.created_at === "string" ? formatDate(bot.created_at) : "—";
  const updatedAtValue =
    typeof bot.updated_at === "string" ? formatDate(bot.updated_at) : "—";

  return (
    <article className={styles.card}>
      <h2 className={styles.title}>{bot.name}</h2>
      {bot.description ? (
        <p className={styles.description}>{bot.description}</p>
      ) : (
        <p className={styles.muted}>Описание не указано</p>
      )}

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.label}>ID</span>
          <span className={styles.value}>{bot.id}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.label}>Аккаунт</span>
          <span className={styles.value}>{accountIdValue}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.label}>Создан</span>
          <span className={styles.value}>{createdAtValue}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.label}>Обновлен</span>
          <span className={styles.value}>{updatedAtValue}</span>
        </div>
      </div>
    </article>
  );
}
