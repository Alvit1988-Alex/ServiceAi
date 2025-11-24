"use client";

import { create } from "zustand";

import {
  getBot,
  getBotStatsSummary,
  listBots,
  updateBot as updateBotApi,
} from "@/app/api/botsApi";
import { Bot, BotUpdate, StatsSummary } from "@/app/api/types";

interface BotsState {
  bots: Bot[];
  selectedBotId: number | null;
  selectedBot: Bot | null;
  statsByBot: Record<number, StatsSummary>;
  loadingBots: boolean;
  loadingStats: boolean;
  error: string | null;
  fetchBots: () => Promise<void>;
  loadBot: (botId: number) => Promise<Bot | null>;
  fetchStatsForBots: () => Promise<void>;
  selectBot: (botId: number | null) => void;
  reloadSelectedBot: () => Promise<void>;
  updateSelectedBot: (data: BotUpdate) => Promise<Bot | null>;
  fetchSelectedBotStats: () => Promise<void>;
}

export const useBotsStore = create<BotsState>((set, get) => ({
  bots: [],
  selectedBotId: null,
  selectedBot: null,
  statsByBot: {},
  loadingBots: false,
  loadingStats: false,
  error: null,
  fetchBots: async () => {
    set({ loadingBots: true, error: null });

    try {
      const bots = await listBots();
      set((state) => {
        const hasSelected = state.selectedBotId && bots.some((bot) => bot.id === state.selectedBotId);
        const selectedBotId = hasSelected ? state.selectedBotId : bots[0]?.id ?? null;
        const selectedBot = selectedBotId ? bots.find((bot) => bot.id === selectedBotId) ?? null : null;
        const statsByBot = Object.fromEntries(
          Object.entries(state.statsByBot).filter(([botId]) =>
            bots.some((bot) => bot.id === Number(botId)),
          ),
        );

        return {
          bots,
          loadingBots: false,
          selectedBotId,
          selectedBot,
          statsByBot,
        };
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить ботов";
      set({ error: message, bots: [], loadingBots: false });
    }
  },
  loadBot: async (botId) => {
    set({ loadingBots: true, error: null });

    try {
      const bot = await getBot(botId);
      set((state) => {
        const existingBot = state.bots.find((item) => item.id === bot.id);
        const mergedBot = existingBot
          ? { ...existingBot, ...bot, channels: bot.channels ?? existingBot.channels }
          : bot;
        const bots = existingBot
          ? state.bots.map((item) => (item.id === bot.id ? mergedBot : item))
          : [...state.bots, mergedBot];

        return {
          bots,
          selectedBotId: bot.id,
          selectedBot: mergedBot,
          loadingBots: false,
        };
      });

      return bot;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось загрузить бота";
      set({ error: message, loadingBots: false });
      return null;
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
          const stats = await getBotStatsSummary(bot.id);
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
  selectBot: (botId) => {
    set((state) => ({
      selectedBotId: botId,
      selectedBot: botId ? state.bots.find((bot) => bot.id === botId) ?? null : null,
    }));
  },
  reloadSelectedBot: async () => {
    const botId = get().selectedBotId;
    if (!botId) {
      return;
    }

    await get().loadBot(botId);
  },
  updateSelectedBot: async (data) => {
    const botId = get().selectedBotId;
    if (!botId) {
      return null;
    }

    set({ loadingBots: true, error: null });

    try {
      const updatedBot = await updateBotApi(botId, data);
      set((state) => ({
        bots: state.bots.map((bot) => (bot.id === updatedBot.id ? updatedBot : bot)),
        selectedBot: updatedBot,
        loadingBots: false,
      }));
      return updatedBot;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось обновить данные бота";
      set({ error: message, loadingBots: false });
      return null;
    }
  },
  fetchSelectedBotStats: async () => {
    const botId = get().selectedBotId;
    if (!botId) {
      return;
    }

    set({ loadingStats: true, error: null });

    try {
      const stats = await getBotStatsSummary(botId);
      set((state) => ({
        statsByBot: { ...state.statsByBot, [botId]: stats },
        loadingStats: false,
      }));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить статистику бота";
      set({ error: message, loadingStats: false });
    }
  },
}));
