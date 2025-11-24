"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import LayoutShell from "@/app/components/layout/LayoutShell";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { useBotsStore } from "@/store/bots.store";
import BotAiInstructions from "@/components/bot/BotAiInstructions";
import BotChannels from "@/components/bot/BotChannels";
import BotOverview from "@/components/bot/BotOverview";
import BotKnowledge from "@/components/bot/BotKnowledge";
import Tabs from "@/components/layout/Tabs";

import styles from "./page.module.css";

interface BotDetailsPageProps {
  params: { botId: string };
}

export default function BotDetailsPage({ params }: BotDetailsPageProps) {
  const botId = useMemo(() => Number(params.botId), [params.botId]);
  const invalidId = Number.isNaN(botId);

  const [activeTab, setActiveTab] = useState<"overview" | "channels" | "ai" | "knowledge">("overview");

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
  const tabs = useMemo(
    () => [
      { value: "overview", label: "Обзор" },
      { value: "channels", label: "Каналы" },
      { value: "ai", label: "ИИ" },
      { value: "knowledge", label: "База знаний" },
    ],
    [],
  );

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
            <div className={styles.content}>
              <Tabs tabs={tabs} activeTab={activeTab} onTabChange={(value) => setActiveTab(value as typeof activeTab)} />

              {activeTab === "overview" && <BotOverview bot={bot} />}
              {activeTab === "channels" && <BotChannels botId={bot.id} />}
              {activeTab === "ai" && <BotAiInstructions botId={bot.id} />}
              {activeTab === "knowledge" && <BotKnowledge botId={bot.id} />}
            </div>
          )}
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
