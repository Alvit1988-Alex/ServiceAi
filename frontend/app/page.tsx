"use client";

import { useEffect, useMemo } from "react";

import LayoutShell from "./components/layout/LayoutShell";
import styles from "./page.module.css";
import { AuthGuard } from "./components/auth/AuthGuard";
import { useBotsStore } from "@/store/bots.store";

function formatSeconds(seconds: number | null | undefined): string {
  if (seconds == null) {
    return "Нет данных";
  }

  if (seconds < 1) {
    return `${Math.round(seconds * 1000)} мс`;
  }

  if (seconds < 60) {
    return `${Math.round(seconds)} с`;
  }

  return `${(seconds / 60).toFixed(1)} мин`;
}

const DASHBOARD_DESCRIPTION =
  "Краткое описание состояния сервисов и полезные показатели. Обновления происходят в реальном времени, чтобы вы могли быстро реагировать на ключевые изменения.";

export default function Home() {
  const {
    bots,
    statsByBot,
    loadingBots,
    loadingStats,
    error,
    fetchBots,
    fetchStatsForBots,
  } = useBotsStore();

  // загрузка списка ботов
  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  // загрузка статистики по ботам
  useEffect(() => {
    if (bots.length > 0) {
      void fetchStatsForBots();
    }
  }, [bots, fetchStatsForBots]);

  const stats = useMemo(() => {
    const summaries = bots
      .map((bot) => statsByBot[bot.id])
      .filter(
        (summary): summary is NonNullable<typeof summary> => Boolean(summary),
      );

    const dialogDurations = summaries
      .map((summary) => summary.timing.average_dialog_duration_seconds)
      .filter((value): value is number => value != null);

    const firstMessageDelays = summaries
      .map(
        (summary) => summary.timing.average_time_to_first_message_seconds,
      )
      .filter((value): value is number => value != null);

    const averageDialogDurationSeconds = dialogDurations.length
      ? dialogDurations.reduce((acc, value) => acc + value, 0) /
        dialogDurations.length
      : null;

    const averageFirstMessageDelaySeconds = firstMessageDelays.length
      ? firstMessageDelays.reduce((acc, value) => acc + value, 0) /
        firstMessageDelays.length
      : null;

    return {
      totalBots: bots.length,
      activeBots: summaries.filter((summary) => summary.dialogs.active > 0)
        .length,
      totalDialogs: summaries.reduce(
        (acc, summary) => acc + summary.dialogs.total,
        0,
      ),
      activeDialogs: summaries.reduce(
        (acc, summary) => acc + summary.dialogs.active,
        0,
      ),
      averageDialogDurationSeconds,
      averageFirstMessageDelaySeconds,
      hasStats: summaries.length > 0,
    };
  }, [bots, statsByBot]);

  const isLoading = loadingBots || loadingStats;
  const hasBots = bots.length > 0;
  const showCards = hasBots && stats.hasStats && !error;

  return (
    <AuthGuard>
      <LayoutShell
        title="Панель управления ServiceAI"
        description={DASHBOARD_DESCRIPTION}
      >
        <section className={styles.loginSection}>
          <div className={styles.loginHeader}>
            <h2 className={styles.loginTitle}>Сводка по сервисам</h2>
            <p className={styles.loginDescription}>
              Добро пожаловать! Используйте сводку ниже, чтобы оперативно
              оценить состояние системы и перейти к нужным разделам.
            </p>
          </div>
          {error && <p className={styles.errorText}>{error}</p>}
          {isLoading && (
            <p className={styles.mutedText}>Загружаем данные...</p>
          )}
          {!isLoading && !error && !hasBots && (
            <p className={styles.mutedText}>
              У вас пока нет ботов. Создайте бота, чтобы увидеть статистику.
            </p>
          )}
        </section>

        {showCards && (
          <div className={styles.cards} aria-label="Ключевые показатели">
            <article className={styles.card}>
              <p className={styles.cardLabel}>Всего ботов</p>
              <p className={styles.cardValue}>{stats.totalBots}</p>
              <p className={styles.cardNote}>
                Активных: {stats.activeBots}
              </p>
            </article>

            <article className={styles.card}>
              <p className={styles.cardLabel}>Диалоги</p>
              <p className={styles.cardValue}>{stats.totalDialogs}</p>
              <p className={styles.cardNote}>
                Активных сейчас: {stats.activeDialogs}
              </p>
            </article>

            <article className={styles.card}>
              <p className={styles.cardLabel}>Длительность диалога</p>
              <p className={styles.cardValue}>
                {formatSeconds(stats.averageDialogDurationSeconds)}
              </p>
              <p className={styles.cardNote}>
                Среднее время от первого до последнего сообщения
              </p>
            </article>

            <article className={styles.card}>
              <p className={styles.cardLabel}>Отклик до первого сообщения</p>
              <p className={styles.cardValue}>
                {formatSeconds(stats.averageFirstMessageDelaySeconds)}
              </p>
              <p className={styles.cardNote}>
                Среднее время ожидания первого ответа
              </p>
            </article>
          </div>
        )}
      </LayoutShell>
    </AuthGuard>
  );
}
