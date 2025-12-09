"use client";

import { httpClient } from "@/app/api/httpClient";
import { create } from "zustand";

export interface BotDTO {
  id: number;
  name: string;
  // остальные поля нам на фронте сейчас не важны
  [key: string]: unknown;
}

export interface BotStatsSummaryDTO {
  dialogs: {
    total: number;
    active: number;
  };
  timing: {
    average_dialog_duration_seconds: number | null;
    average_time_to_first_message_seconds: number | null;
  };
  // запас под дополнительные поля
  [key: string]: unknown;
}

interface BotsState {
  bots: BotDTO[];
  statsByBot: Record<number, BotStatsSummaryDTO>;
  loadingBots: boolean;
  loadingStats: boolean;
  error: string | null;

  fetchBots: () => Promise<void>;
  fetchStatsForBots: () => Promise<void>;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await httpClient(path, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    // важно — кидаем ошибку, но не трогаем стор здесь
    throw new Error(
      `Ошибка запроса ${path}: ${response.status} ${response.statusText}`,
    );
  }

  return (await response.json()) as T;
}

export const useBotsStore = create<BotsState>((set, get) => ({
  bots: [],
  statsByBot: {},
  loadingBots: false,
  loadingStats: false,
  error: null,

  /**
   * Загрузка списка ботов.
   * Никаких внутренних рекурсий или подписок — только set() по результату.
   */
  async fetchBots() {
    set({ loadingBots: true, error: null });

    try {
      const bots = await apiGet<BotDTO[]>("/bots");
      set({
        bots,
        loadingBots: false,
      });
    } catch (error) {
      console.error("Failed to fetch bots", error);
      const message =
        error instanceof Error
          ? error.message
          : "Не удалось загрузить список ботов";
      set({
        loadingBots: false,
        error: message,
      });
    }
  },

  /**
   * Загрузка сводной статистики по всем ботам.
   * Вызывается только после fetchBots (когда в сторе уже есть bots).
   */
  async fetchStatsForBots() {
    const { bots } = get();

    // если ботов нет — просто чистим статистику и выходим
    if (!bots.length) {
      set({ statsByBot: {}, loadingStats: false });
      return;
    }

    set({ loadingStats: true, error: null });

    try {
      // здесь можно будет заменить эндпоинт на тот, что реализован на бэке
      const results = await Promise.all(
        bots.map(async (bot) => {
          const stats = await apiGet<BotStatsSummaryDTO>(
            `/bots/${bot.id}/stats/summary`,
          );
          return [bot.id, stats] as const;
        }),
      );

      const statsByBot: Record<number, BotStatsSummaryDTO> = {};
      for (const [botId, stats] of results) {
        statsByBot[botId] = stats;
      }

      set({
        statsByBot,
        loadingStats: false,
      });
    } catch (error) {
      console.error("Failed to fetch bots stats", error);
      const message =
        error instanceof Error
          ? error.message
          : "Не удалось загрузить статистику ботов";
      set({
        loadingStats: false,
        error: message,
      });
    }
  },
}));
