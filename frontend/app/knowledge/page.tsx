"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import botSelectionStyles from "@/app/components/ui/BotSelection.module.css";
import BotAiSetup from "@/components/bot/BotAiSetup";
import { useBotsStore } from "@/store/bots.store";

export default function KnowledgePage() {
  const router = useRouter();
  const { bots, selectedBotId, loadingBots, error, fetchBots, selectBot } = useBotsStore();

  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  const hasBots = bots.length > 0;

  return (
    <AuthGuard>
      <LayoutShell title="ИИ и база знаний" description="Настройка ИИ и базы знаний.">
        {error && <p className={botSelectionStyles.error}>{error}</p>}

        {!error && loadingBots && (
          <p style={{ color: "var(--color-text-muted)" }}>Загружаем список ботов...</p>
        )}

        {!error && !loadingBots && !hasBots && (
          <div className={botSelectionStyles.container}>
            <p className={botSelectionStyles.message}>Нет ботов</p>
            <button className="volume-button" type="button" onClick={() => router.push("/bots")}>
              Перейти в Боты
            </button>
          </div>
        )}

        {!error && !loadingBots && hasBots && selectedBotId == null && (
          <div className={botSelectionStyles.container}>
            <p className={botSelectionStyles.message}>
              Выберите бота, чтобы настроить ИИ и базу знаний.
            </p>
            <div className={botSelectionStyles.list}>
              {bots.map((bot) => (
                <button
                  key={bot.id}
                  type="button"
                  className="volume-button"
                  onClick={() => selectBot(bot.id)}
                >
                  {bot.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {selectedBotId != null && <BotAiSetup botId={selectedBotId} />}
      </LayoutShell>
    </AuthGuard>
  );
}
