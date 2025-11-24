"use client";

import { create } from "zustand";

import {
  closeDialog as closeDialogApi,
  getDialog,
  listDialogs,
  lockDialog as lockDialogApi,
  sendOperatorMessage,
  unlockDialog as unlockDialogApi,
} from "@/app/api/dialogsApi";
import {
  DialogDetail,
  DialogMessage,
  DialogShort,
  DialogStatus,
  ListResponse,
} from "@/app/api/types";

interface DialogsState {
  dialogsByBot: Record<number, DialogShort[]>;
  paginationByBot: Record<number, Pick<ListResponse<DialogShort>, "page" | "per_page" | "total" | "has_next">>;
  dialogDetails: Record<number, DialogDetail>;
  selectedDialogId: number | null;
  loadingList: boolean;
  loadingDialog: boolean;
  sendingMessage: boolean;
  updatingDialog: boolean;
  error: string | null;
  fetchDialogs: (
    botId: number,
    params?: Parameters<typeof listDialogs>[1],
  ) => Promise<ListResponse<DialogShort> | null>;
  fetchDialog: (botId: number, dialogId: number) => Promise<DialogDetail | null>;
  setSelectedDialog: (dialogId: number | null) => void;
  sendMessage: (
    botId: number,
    dialogId: number,
    payload: { text?: string | null; payload?: Record<string, unknown> | null },
  ) => Promise<DialogMessage | null>;
  lockDialog: (botId: number, dialogId: number) => Promise<DialogDetail | null>;
  unlockDialog: (botId: number, dialogId: number) => Promise<DialogDetail | null>;
  closeDialog: (botId: number, dialogId: number) => Promise<DialogDetail | null>;
  applyDialogCreated: (dialog: DialogDetail | DialogShort) => void;
  applyDialogUpdated: (dialog: DialogDetail | DialogShort) => void;
  applyDialogLocked: (dialog: DialogDetail | DialogShort) => void;
  applyDialogUnlocked: (dialog: DialogDetail | DialogShort) => void;
  applyMessageCreated: (message: DialogMessage) => void;
}

function mapDetailToShort(dialog: DialogDetail): DialogShort {
  const { messages, ...rest } = dialog;
  const lastMessage = messages[messages.length - 1];

  return {
    ...rest,
    last_message: lastMessage ?? dialog.last_message,
  };
}

function mergeMessages(existing: DialogMessage[], incoming: DialogMessage[]): DialogMessage[] {
  const map = new Map<number, DialogMessage>();
  [...existing, ...incoming].forEach((message) => {
    map.set(message.id, message);
  });

  return Array.from(map.values()).sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
}

function isDialogDetail(dialog: DialogDetail | DialogShort): dialog is DialogDetail {
  return (dialog as DialogDetail).messages !== undefined;
}

export const useDialogsStore = create<DialogsState>((set, get) => ({
  dialogsByBot: {},
  paginationByBot: {},
  dialogDetails: {},
  selectedDialogId: null,
  loadingList: false,
  loadingDialog: false,
  sendingMessage: false,
  updatingDialog: false,
  error: null,
  fetchDialogs: async (botId, params = {}) => {
    set({ loadingList: true, error: null });

    try {
      const response = await listDialogs(botId, params);
      set((state) => ({
        dialogsByBot: { ...state.dialogsByBot, [botId]: response.items },
        paginationByBot: {
          ...state.paginationByBot,
          [botId]: {
            page: response.page,
            per_page: response.per_page,
            total: response.total,
            has_next: response.has_next,
          },
        },
        loadingList: false,
      }));

      return response;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Не удалось загрузить список диалогов";
      set({ error: message, loadingList: false });
      return null;
    }
  },
  fetchDialog: async (botId, dialogId) => {
    set({ loadingDialog: true, error: null, selectedDialogId: dialogId });

    try {
      const dialog = await getDialog(botId, dialogId);
      set((state) => ({
        dialogDetails: { ...state.dialogDetails, [dialog.id]: dialog },
        dialogsByBot: {
          ...state.dialogsByBot,
          [botId]: state.dialogsByBot[botId]
            ? state.dialogsByBot[botId].map((item) =>
                item.id === dialog.id ? mapDetailToShort(dialog) : item,
              )
            : [mapDetailToShort(dialog)],
        },
        loadingDialog: false,
      }));
      return dialog;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось загрузить диалог";
      set({ error: message, loadingDialog: false });
      return null;
    }
  },
  setSelectedDialog: (dialogId) => set({ selectedDialogId: dialogId }),
  sendMessage: async (botId, dialogId, payload) => {
    set({ sendingMessage: true, error: null });

    try {
      const message = await sendOperatorMessage(botId, dialogId, payload);

      set((state) => {
        const existingDetail = state.dialogDetails[dialogId];
        const updatedDetail = existingDetail
          ? {
              ...existingDetail,
              messages: mergeMessages(existingDetail.messages, [message]),
              last_message_at: message.created_at,
              status:
                existingDetail.status === DialogStatus.WAIT_USER
                  ? DialogStatus.WAIT_OPERATOR
                  : existingDetail.status,
            }
          : undefined;

        const botIdFromState = existingDetail?.bot_id ?? botId;
        const list = botIdFromState ? state.dialogsByBot[botIdFromState] ?? [] : [];
        const updatedList = botIdFromState
          ? list.some((item) => item.id === dialogId)
            ? list.map((item) =>
                item.id === dialogId
                  ? {
                      ...item,
                      last_message: message,
                      last_message_at: message.created_at,
                      status:
                        item.status === DialogStatus.WAIT_USER
                          ? DialogStatus.WAIT_OPERATOR
                          : item.status,
                    }
                  : item,
              )
            : list
          : list;

        return {
          dialogDetails: updatedDetail
            ? { ...state.dialogDetails, [dialogId]: updatedDetail }
            : state.dialogDetails,
          dialogsByBot: botIdFromState
            ? { ...state.dialogsByBot, [botIdFromState]: updatedList }
            : state.dialogsByBot,
          sendingMessage: false,
        };
      });

      return message;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось отправить сообщение";
      set({ error: message, sendingMessage: false });
      return null;
    }
  },
  lockDialog: async (botId, dialogId) => {
    set({ updatingDialog: true, error: null });

    try {
      const dialog = await lockDialogApi(botId, dialogId);
      set((state) => ({
        dialogDetails: { ...state.dialogDetails, [dialog.id]: dialog },
        dialogsByBot: {
          ...state.dialogsByBot,
          [botId]: state.dialogsByBot[botId]
            ? state.dialogsByBot[botId].map((item) =>
                item.id === dialog.id ? mapDetailToShort(dialog) : item,
              )
            : [mapDetailToShort(dialog)],
        },
        updatingDialog: false,
      }));
      return dialog;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось заблокировать диалог";
      set({ error: message, updatingDialog: false });
      return null;
    }
  },
  unlockDialog: async (botId, dialogId) => {
    set({ updatingDialog: true, error: null });

    try {
      const dialog = await unlockDialogApi(botId, dialogId);
      set((state) => ({
        dialogDetails: { ...state.dialogDetails, [dialog.id]: dialog },
        dialogsByBot: {
          ...state.dialogsByBot,
          [botId]: state.dialogsByBot[botId]
            ? state.dialogsByBot[botId].map((item) =>
                item.id === dialog.id ? mapDetailToShort(dialog) : item,
              )
            : [mapDetailToShort(dialog)],
        },
        updatingDialog: false,
      }));
      return dialog;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось разблокировать диалог";
      set({ error: message, updatingDialog: false });
      return null;
    }
  },
  closeDialog: async (botId, dialogId) => {
    set({ updatingDialog: true, error: null });

    try {
      const dialog = await closeDialogApi(botId, dialogId);
      set((state) => ({
        dialogDetails: { ...state.dialogDetails, [dialog.id]: dialog },
        dialogsByBot: {
          ...state.dialogsByBot,
          [botId]: state.dialogsByBot[botId]
            ? state.dialogsByBot[botId].map((item) =>
                item.id === dialog.id ? mapDetailToShort(dialog) : item,
              )
            : [mapDetailToShort(dialog)],
        },
        updatingDialog: false,
      }));
      return dialog;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось закрыть диалог";
      set({ error: message, updatingDialog: false });
      return null;
    }
  },
  applyDialogCreated: (dialog) => {
    const short = isDialogDetail(dialog) ? mapDetailToShort(dialog) : dialog;
    const detail = isDialogDetail(dialog) ? dialog : undefined;

    set((state) => {
      const botId = dialog.bot_id;
      const list = state.dialogsByBot[botId] ?? [];
      const updatedList = [short, ...list.filter((item) => item.id !== dialog.id)];

      return {
        dialogsByBot: { ...state.dialogsByBot, [botId]: updatedList },
        dialogDetails: detail
          ? { ...state.dialogDetails, [dialog.id]: detail }
          : state.dialogDetails,
      };
    });
  },
  applyDialogUpdated: (dialog) => {
    const short = isDialogDetail(dialog) ? mapDetailToShort(dialog) : dialog;
    const detail = isDialogDetail(dialog) ? dialog : undefined;

    set((state) => {
      const botId = dialog.bot_id;
      const list = state.dialogsByBot[botId] ?? [];
      const existingDetail = state.dialogDetails[dialog.id];
      const mergedDetail = detail
        ? {
            ...detail,
            messages: existingDetail
              ? mergeMessages(existingDetail.messages, detail.messages)
              : detail.messages,
          }
        : existingDetail;
      const updatedList = list.some((item) => item.id === dialog.id)
        ? list.map((item) => (item.id === dialog.id ? { ...item, ...short } : item))
        : [short, ...list];

      return {
        dialogsByBot: { ...state.dialogsByBot, [botId]: updatedList },
        dialogDetails: mergedDetail
          ? { ...state.dialogDetails, [dialog.id]: mergedDetail }
          : state.dialogDetails,
      };
    });
  },
  applyDialogLocked: (dialog) => get().applyDialogUpdated(dialog),
  applyDialogUnlocked: (dialog) => get().applyDialogUpdated(dialog),
  applyMessageCreated: (message) => {
    set((state) => {
      const existingDetail = state.dialogDetails[message.dialog_id];
      const updatedDetail = existingDetail
        ? {
            ...existingDetail,
            messages: mergeMessages(existingDetail.messages, [message]),
            last_message_at: message.created_at,
          }
        : undefined;

      const botId = existingDetail?.bot_id;
      const list = botId ? state.dialogsByBot[botId] ?? [] : [];
      const updatedList = botId
        ? list.some((item) => item.id === message.dialog_id)
          ? list.map((item) =>
              item.id === message.dialog_id
                ? { ...item, last_message: message, last_message_at: message.created_at }
                : item,
            )
          : list
        : list;

      return {
        dialogDetails: updatedDetail
          ? { ...state.dialogDetails, [message.dialog_id]: updatedDetail }
          : state.dialogDetails,
        dialogsByBot: botId
          ? { ...state.dialogsByBot, [botId]: updatedList }
          : state.dialogsByBot,
      };
    });
  },
}));
