import Link from "next/link";

import { Bot } from "@/app/api/types";

import styles from "./BotCard.module.css";

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

interface BotCardProps {
  bot: Bot;
}

export function BotCard({ bot }: BotCardProps) {
  const createdAt = formatDate(bot.created_at);

  return (
    <Link
      href={`/bots/${bot.id}`}
      className={styles.card}
      aria-label={`Открыть бота ${bot.name}`}
    >
      <div className={styles.header}>
        <h3 className={styles.name}>{bot.name}</h3>
        <span className={styles.id}>ID: {bot.id}</span>
      </div>

      {bot.description ? (
        <p className={styles.description}>{bot.description}</p>
      ) : (
        <p className={styles.muted}>Описание не указано</p>
      )}

      <div className={styles.meta}>
        <span className={styles.label}>Аккаунт</span>
        <span className={styles.value}>#{bot.account_id}</span>
        <span className={styles.label}>Создан</span>
        <span className={styles.value}>{createdAt}</span>
      </div>
    </Link>
  );
}
