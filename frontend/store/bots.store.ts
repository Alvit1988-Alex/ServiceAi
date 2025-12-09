"use client";

import { httpClient } from "@/app/api/httpClient";
import { createBot as createBotApi } from "@/app/api/botsApi";
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

  /**
   * Текущий выбранный бот (используется на странице бота и в поиске).
   */
  selectedBotId: number | null;
  selectedBot: BotDTO | null;

  /**
   * Загрузка списка ботов.
   */
  fetchBots: () => Promise<void>;

  /**
   * Загрузка сводной статистики для всех ботов.
   */
  fetchStatsForBots: () => Promise<void>;

  /**
   * Создание нового бота.
   */
  createBot: (name: string, description?: string | null) => Promise<void>;

  /**
   * Установка выбранного бота по id.
   */
  selectBot: (id: number | null) => void;

  /**
   * Перезагрузка данных выбранного бота с бэкенда.
   */
  reloadSelectedBot: () => Promise<void>;
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
  selectedBotId: null,
  selectedBot: null,

  /**
   * Загрузка списка ботов.
   * Никаких внутренних рекурсий или подписок — только set() по результату.
   */
  async fetchBots() {
    set({ loadingBots: true, error: null });

    try {
      const data = await apiGet<{ items: BotDTO[] }>("/bots");
      const items = data.items;

      set((state) => {
        const nextSelectedBot =
          state.selectedBotId != null
            ? items.find((bot) => bot.id === state.selectedBotId) ?? state.selectedBot
            : state.selectedBot;

        return {
          bots: items,
          loadingBots: false,
          selectedBot: nextSelectedBot,
        };
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
   * Вызывается только после fetchBots (когда в сторе уже есть список ботов).
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
      console.error("Failed to fetch bot stats", error);
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

  /**
   * Создание нового бота.
   */
  async createBot(name: string, description?: string | null) {
    set({ loadingBots: true, error: null });

    try {
      const newBot = await createBotApi({ name, description });

      set((state) => ({
        bots: [...state.bots, newBot],
        loadingBots: false,
      }));
    } catch (error) {
      console.error("Failed to create bot", error);
      const message =
        error instanceof Error
          ? error.message
          : "Не удалось создать бота";

      set({
        loadingBots: false,
        error: message,
      });
    }
  },

  /**
   * Установка выбранного бота по идентификатору.
   */
  selectBot(id: number | null) {
    set((state) => {
      if (id == null) {
        return {
          selectedBotId: null,
          selectedBot: null,
        };
      }

      const botFromList = state.bots.find((bot) => bot.id === id) ?? null;

      return {
        selectedBotId: id,
        selectedBot: botFromList ?? state.selectedBot,
      };
    });
  },

  /**
   * Перезагрузка данных выбранного бота с сервера.
   * Если selectedBotId не задан, функция ничего не делает.
   */
  async reloadSelectedBot() {
    const { selectedBotId } = get();

    if (!selectedBotId) {
      return;
    }

    set({ loadingBots: true, error: null });

    try {
      const bot = await apiGet<BotDTO>(`/bots/${selectedBotId}`);

      set((state) => {
        const bots = state.bots.some((item) => item.id === bot.id)
          ? state.bots.map((item) => (item.id === bot.id ? bot : item))
          : [...state.bots, bot];

        return {
          bots,
          selectedBotId,
          selectedBot: bot,
          loadingBots: false,
        };
      });
    } catch (error) {
      console.error("Failed to reload selected bot", error);
      const message =
        error instanceof Error
          ? error.message
          : "Не удалось загрузить данные бота";

      set({
        loadingBots: false,
        error: message,
      });
    }
  },
}));
