"use client";

import Link from "next/link";
import { useEffect, useMemo } from "react";

import LayoutShell from "@/app/components/layout/LayoutShell";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { useBotsStore } from "@/store/bots.store";

import styles from "./page.module.css";

interface BotDetailsPageProps {
  params: { botId: string };
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

export default function BotDetailsPage({ params }: BotDetailsPageProps) {
  const botId = useMemo(() => Number(params.botId), [params.botId]);
  const invalidId = Number.isNaN(botId);

  const { bots, selectedBot, loadingBots, error, fetchBots, reloadSelectedBot, selectBot } = useBotsStore();

  useEffect(() => {
    if (!invalidId) {
      selectBot(botId);
    }
  }, [botId, invalidId, selectBot]);

  useEffect(() => {
    if (invalidId) {
      return;
    }

    if (bots.length === 0) {
      void fetchBots();
      return;
    }

    const hasBot = bots.some((bot) => bot.id === botId);
    if (!hasBot) {
      void reloadSelectedBot();
    }
  }, [botId, bots, fetchBots, invalidId, reloadSelectedBot]);

  const bot = useMemo(() => bots.find((item) => item.id === botId) ?? selectedBot, [botId, bots, selectedBot]);

  return (
    <AuthGuard>
      <LayoutShell title="Бот" description="Просмотр информации о боте">
        <div className={styles.container}>
          <Link className={styles.backLink} href="/bots">
            ← Назад к списку ботов
          </Link>

          {invalidId && <p className={styles.error}>Некорректный идентификатор бота.</p>}
          {!invalidId && error && <p className={styles.error}>{error}</p>}
          {!invalidId && loadingBots && <p className={styles.muted}>Загружаем данные бота...</p>}

          {!invalidId && !loadingBots && !bot && !error && (
            <p className={styles.muted}>Бот не найден.</p>
          )}

          {bot && (
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
          )}
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
