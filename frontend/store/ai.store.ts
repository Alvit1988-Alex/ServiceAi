"use client";

import { create } from "zustand";

import { getBotAiInstructions, updateBotAiInstructions } from "@/app/api/aiApi";
import {
  deleteKnowledgeItem as deleteKnowledgeItemApi,
  getKnowledgeItems,
  uploadKnowledgeItem as uploadKnowledgeItemApi,
} from "@/app/api/knowledgeApi";
import { BotAiInstructions, KnowledgeFile } from "@/app/api/types";

interface KnowledgePaginationState {
  page: number;
  per_page: number;
  total: number;
  has_next: boolean;
}

const KNOWLEDGE_PER_PAGE = 10;

function buildPagination(
  total: number,
  perPage: number,
  currentPage: number = 1,
): KnowledgePaginationState {
  const safePerPage = Math.max(1, perPage);
  const maxPage = Math.max(1, Math.ceil(total / safePerPage));
  const page = Math.min(Math.max(1, currentPage), maxPage);

  return {
    page,
    per_page: safePerPage,
    total,
    has_next: page < maxPage,
  };
}

interface AiState {
  instructionsByBot: Record<number, BotAiInstructions>;
  knowledgeByBot: Record<number, KnowledgeFile[]>;
  knowledgePaginationByBot: Record<number, KnowledgePaginationState>;
  loadingInstructions: boolean;
  savingInstructions: boolean;
  loadingKnowledge: boolean;
  uploadingKnowledge: boolean;
  deletingKnowledge: boolean;
  error: string | null;
  loadInstructions: (botId: number) => Promise<BotAiInstructions | null>;
  saveInstructions: (botId: number, systemPrompt: string) => Promise<BotAiInstructions | null>;
  loadKnowledge: (botId: number) => Promise<KnowledgeFile[] | null>;
  reloadKnowledge: (botId: number) => Promise<KnowledgeFile[] | null>;
  uploadKnowledgeItem: (botId: number, file: File) => Promise<KnowledgeFile | null>;
  deleteKnowledgeItem: (botId: number, fileId: number) => Promise<boolean>;
  changeKnowledgePage: (botId: number, page: number) => void;
}

export const useAiStore = create<AiState>((set, get) => ({
  instructionsByBot: {},
  knowledgeByBot: {},
  knowledgePaginationByBot: {},
  loadingInstructions: false,
  savingInstructions: false,
  loadingKnowledge: false,
  uploadingKnowledge: false,
  deletingKnowledge: false,
  error: null,
  loadInstructions: async (botId) => {
    const existing = get().instructionsByBot[botId];
    if (existing) {
      return existing;
    }

    set({ loadingInstructions: true, error: null });

    try {
      const instructions = await getBotAiInstructions(botId);
      set((state) => ({
        instructionsByBot: { ...state.instructionsByBot, [botId]: instructions },
        loadingInstructions: false,
      }));
      return instructions;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить инструкции ИИ";
      set({ error: message, loadingInstructions: false });
      return null;
    }
  },
  saveInstructions: async (botId, systemPrompt) => {
    set({ savingInstructions: true, error: null });

    try {
      const updated = await updateBotAiInstructions(botId, systemPrompt);
      set((state) => ({
        instructionsByBot: { ...state.instructionsByBot, [botId]: updated },
        savingInstructions: false,
      }));
      return updated;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось обновить инструкции ИИ";
      set({ error: message, savingInstructions: false });
      return null;
    }
  },
  loadKnowledge: async (botId) => {
    const existing = get().knowledgeByBot[botId];
    if (existing) {
      return existing;
    }

    return get().reloadKnowledge(botId);
  },
  reloadKnowledge: async (botId) => {
    set({ loadingKnowledge: true, error: null });

    try {
      const response = await getKnowledgeItems(botId);
      set((state) => ({
        knowledgeByBot: { ...state.knowledgeByBot, [botId]: response.items },
        knowledgePaginationByBot: {
          ...state.knowledgePaginationByBot,
          [botId]: buildPagination(
            response.items.length,
            state.knowledgePaginationByBot[botId]?.per_page ?? KNOWLEDGE_PER_PAGE,
            state.knowledgePaginationByBot[botId]?.page,
          ),
        },
        loadingKnowledge: false,
      }));
      return response.items;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить базу знаний";
      set({ error: message, loadingKnowledge: false });
      return null;
    }
  },
  uploadKnowledgeItem: async (botId, file) => {
    set({ uploadingKnowledge: true, error: null });

    try {
      const uploadedItem = await uploadKnowledgeItemApi(botId, file);
      set((state) => {
        const existing = state.knowledgeByBot[botId];
        if (existing) {
          const updated = [uploadedItem, ...existing.filter((item) => item.id !== uploadedItem.id)];
          const perPage = state.knowledgePaginationByBot[botId]?.per_page ?? KNOWLEDGE_PER_PAGE;
          return {
            knowledgeByBot: { ...state.knowledgeByBot, [botId]: updated },
            knowledgePaginationByBot: {
              ...state.knowledgePaginationByBot,
              [botId]: buildPagination(updated.length, perPage, 1),
            },
            uploadingKnowledge: false,
          };
        }

        return { uploadingKnowledge: false };
      });

      if (!get().knowledgeByBot[botId]) {
        await get().reloadKnowledge(botId);
      }

      return uploadedItem;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить файл базы знаний";
      set({ error: message, uploadingKnowledge: false });
      return null;
    }
  },
  deleteKnowledgeItem: async (botId, fileId) => {
    set({ deletingKnowledge: true, error: null });

    try {
      await deleteKnowledgeItemApi(botId, fileId);
      set((state) => {
        const existing = state.knowledgeByBot[botId];
        if (existing) {
          const updated = existing.filter((item) => item.id !== fileId);
          const perPage = state.knowledgePaginationByBot[botId]?.per_page ?? KNOWLEDGE_PER_PAGE;
          return {
            knowledgeByBot: { ...state.knowledgeByBot, [botId]: updated },
            knowledgePaginationByBot: {
              ...state.knowledgePaginationByBot,
              [botId]: buildPagination(
                updated.length,
                perPage,
                state.knowledgePaginationByBot[botId]?.page,
              ),
            },
            deletingKnowledge: false,
          };
        }

        return { deletingKnowledge: false };
      });

      if (!get().knowledgeByBot[botId]) {
        await get().reloadKnowledge(botId);
      }

      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось удалить файл базы знаний";
      set({ error: message, deletingKnowledge: false });
      return false;
    }
  },
  changeKnowledgePage: (botId, page) => {
    set((state) => {
      const perPage = state.knowledgePaginationByBot[botId]?.per_page ?? KNOWLEDGE_PER_PAGE;
      const total = state.knowledgeByBot[botId]?.length ?? 0;

      return {
        knowledgePaginationByBot: {
          ...state.knowledgePaginationByBot,
          [botId]: buildPagination(total, perPage, page),
        },
      };
    });
  },
}));
