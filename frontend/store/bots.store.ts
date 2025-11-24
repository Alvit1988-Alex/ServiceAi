"use client";

import { create } from "zustand";

import { fetchBotStats, fetchBots } from "@/app/api/botsApi";
import { Bot, StatsSummary } from "@/app/api/types";

interface BotsState {
  bots: Bot[];
  statsByBot: Record<number, StatsSummary>;
  loadingBots: boolean;
  loadingStats: boolean;
  error: string | null;
  fetchBots: () => Promise<void>;
  fetchStatsForBots: () => Promise<void>;
}

export const useBotsStore = create<BotsState>((set, get) => ({
  bots: [],
  statsByBot: {},
  loadingBots: false,
  loadingStats: false,
  error: null,
  fetchBots: async () => {
    set({ loadingBots: true, error: null });

    try {
      const bots = await fetchBots();
      set({ bots, loadingBots: false });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить ботов";
      set({ error: message, bots: [], loadingBots: false });
    }
  },
  fetchStatsForBots: async () => {
    const bots = get().bots;
    if (bots.length === 0) {
      set({ statsByBot: {}, loadingStats: false });
      return;
    }

    set({ loadingStats: true, error: null });

    try {
      const statsEntries = await Promise.all(
        bots.map(async (bot) => {
          const stats = await fetchBotStats(bot.id);
          return [bot.id, stats] as const;
        }),
      );

      const statsByBot = Object.fromEntries(statsEntries);
      set({ statsByBot, loadingStats: false });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Не удалось загрузить статистику ботов";
      set({ error: message, statsByBot: {}, loadingStats: false });
    }
  },
}));
