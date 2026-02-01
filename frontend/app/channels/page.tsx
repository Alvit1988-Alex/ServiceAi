"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
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
        {error && <p style={{ color: "#dc2626", fontWeight: 600 }}>{error}</p>}

        {!error && loadingBots && (
          <p style={{ color: "var(--color-text-muted)" }}>Загружаем список ботов...</p>
        )}

        {!error && !loadingBots && !hasBots && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "18px",
              padding: "1.5rem 0",
            }}
          >
            <p style={{ margin: 0, color: "var(--color-text-muted)" }}>Нет ботов</p>
            <button className="volume-button" type="button" onClick={() => router.push("/bots")}>
              Перейти в Боты
            </button>
          </div>
        )}

        {!error && !loadingBots && hasBots && selectedBotId == null && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "18px",
              alignItems: "center",
              padding: "1.5rem 0",
            }}
          >
            <p style={{ margin: 0, color: "var(--color-text-muted)" }}>
              Выберите бота, чтобы управлять каналами.
            </p>
            <div style={{ width: "100%", maxWidth: "520px", display: "flex", flexDirection: "column", gap: "18px" }}>
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
