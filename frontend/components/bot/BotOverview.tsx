"use client";

import { Bot } from "@/app/api/types";

import styles from "./BotOverview.module.css";

interface BotOverviewProps {
  bot: Bot;
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
          <span className={styles.value}>#{bot.account_id}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.label}>Создан</span>
          <span className={styles.value}>{formatDate(bot.created_at)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.label}>Обновлен</span>
          <span className={styles.value}>{formatDate(bot.updated_at)}</span>
        </div>
      </div>
    </article>
  );
}
