"use client";

import { useEffect } from "react";

import { BotCard } from "@/app/components/bots/BotCard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { useBotsStore } from "@/store/bots.store";

import styles from "./page.module.css";

const DESCRIPTION =
  "Просматривайте ботов, переходите к их деталям и отслеживайте состояние из единого списка.";

export default function BotsPage() {
  const { bots, loadingBots, error, fetchBots } = useBotsStore();

  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  const hasBots = bots.length > 0;

  return (
    <AuthGuard>
      <LayoutShell title="Боты" description={DESCRIPTION}>
        <section className={styles.section}>
          <div className={styles.header}>
            <h2 className={styles.title}>Список ботов</h2>
            <p className={styles.description}>
              Выберите бота, чтобы открыть его подробности или обновить настройки.
            </p>
          </div>

          {error && <p className={styles.error}>{error}</p>}
          {!error && loadingBots && (
            <p className={styles.status}>Загружаем список ботов...</p>
          )}
          {!error && !loadingBots && !hasBots && (
            <p className={styles.status}>Пока нет доступных ботов.</p>
          )}

          {!error && hasBots && (
            <div className={styles.grid}>
              {bots.map((bot) => (
                <BotCard key={bot.id} bot={bot} />
              ))}
            </div>
          )}
        </section>
      </LayoutShell>
    </AuthGuard>
  );
}
