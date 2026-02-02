"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import botSelectionStyles from "@/app/components/ui/BotSelection.module.css";
import BotChannels from "@/components/bot/BotChannels";
import { useBotsStore } from "@/store/bots.store";

export default function ChannelsPage() {
  const router = useRouter();
  const { bots, selectedBotId, loadingBots, error, fetchBots, selectBot } = useBotsStore();

  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  const hasBots = bots.length > 0;

  return (
    <AuthGuard>
      <LayoutShell title="Каналы" description="Управление каналами.">
        {error && <p className={botSelectionStyles.error}>{error}</p>}

        {!error && loadingBots && (
          <p className={botSelectionStyles.message}>Загружаем список ботов...</p>
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
            <p className={botSelectionStyles.message}>Выберите бота, чтобы управлять каналами.</p>
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

        {selectedBotId != null && <BotChannels botId={selectedBotId} />}
      </LayoutShell>
    </AuthGuard>
  );
}
