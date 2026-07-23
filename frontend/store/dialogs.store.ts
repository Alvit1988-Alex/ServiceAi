"use client";

import { create } from "zustand";

import {
  closeDialog as closeDialogApi,
  getDialog,
  getWaitingOperatorDialogsCount,
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
  waitingOperatorCount: number;
  waitingOperatorCountLoaded: boolean;
  dialogWaitOperatorState: Record<number, boolean>;
  dialogUpdateRevision: number;
  latestDialogUpdate: DialogDetail | DialogShort | null;
  fetchWaitingOperatorCount: (shouldApply?: () => boolean) => Promise<boolean>;
  resetWaitingOperatorCount: () => void;
  reconcileWaitingOperatorCountForDialog: (dialog: DialogDetail | DialogShort) => boolean;
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
  applyDialogCreated: (dialog: DialogDetail | DialogShort) => boolean;
  applyDialogUpdated: (dialog: DialogDetail | DialogShort) => boolean;
  applyDialogLocked: (dialog: DialogDetail | DialogShort) => boolean;
  applyDialogUnlocked: (dialog: DialogDetail | DialogShort) => boolean;
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

function contributesToWaitingOperatorCount(dialog: DialogDetail | DialogShort): boolean {
  return (
    dialog.status === DialogStatus.WAIT_OPERATOR &&
    !dialog.closed &&
    dialog.assigned_admin_id == null
  );
}

function findKnownWaitingState(
  state: DialogsState,
  dialog: DialogDetail | DialogShort,
): boolean | undefined {
  if (Object.prototype.hasOwnProperty.call(state.dialogWaitOperatorState, dialog.id)) {
    return state.dialogWaitOperatorState[dialog.id];
  }

  const existingDetail = state.dialogDetails[dialog.id];
  if (existingDetail) {
    return contributesToWaitingOperatorCount(existingDetail);
  }

  const existingListItem = state.dialogsByBot[dialog.bot_id]?.find((item) => item.id === dialog.id);
  if (existingListItem) {
    return contributesToWaitingOperatorCount(existingListItem);
  }

  return undefined;
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
  waitingOperatorCount: 0,
  waitingOperatorCountLoaded: false,
  dialogWaitOperatorState: {},
  dialogUpdateRevision: 0,
  latestDialogUpdate: null,
  fetchWaitingOperatorCount: async (shouldApply) => {
    try {
      const response = await getWaitingOperatorDialogsCount();
      const isCurrent = shouldApply ? shouldApply() : true;
      if (!isCurrent) {
        return false;
      }

      set({
        waitingOperatorCount: response.count,
        waitingOperatorCountLoaded: true,
        dialogWaitOperatorState: {},
      });
      return true;
    } catch (error) {
      const isCurrent = shouldApply ? shouldApply() : true;
      if (!isCurrent) {
        return false;
      }

      const message = error instanceof Error ? error.message : "Не удалось загрузить счётчик диалогов";
      set({ error: message });
      throw error;
    }
  },
  resetWaitingOperatorCount: () =>
    set({
      waitingOperatorCount: 0,
      waitingOperatorCountLoaded: false,
      dialogWaitOperatorState: {},
      dialogUpdateRevision: 0,
      latestDialogUpdate: null,
    }),
  reconcileWaitingOperatorCountForDialog: (dialog) => {
    const state = get();
    const previous = findKnownWaitingState(state, dialog);
    const next = contributesToWaitingOperatorCount(dialog);

    set((current) => {
      const delta = previous === undefined || previous === next ? 0 : next ? 1 : -1;
      return {
        waitingOperatorCount: Math.max(0, current.waitingOperatorCount + delta),
        dialogWaitOperatorState: { ...current.dialogWaitOperatorState, [dialog.id]: next },
      };
    });

    return previous === undefined;
  },
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
        dialogWaitOperatorState: {
          ...state.dialogWaitOperatorState,
          ...Object.fromEntries(response.items.map((dialog) => [dialog.id, contributesToWaitingOperatorCount(dialog)])),
        },
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
        dialogWaitOperatorState: {
          ...state.dialogWaitOperatorState,
          [dialog.id]: contributesToWaitingOperatorCount(dialog),
        },
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
      const existing = get().dialogDetails[dialogId] ?? get().dialogsByBot[botId]?.find((item) => item.id === dialogId);
      if (existing) {
        get().reconcileWaitingOperatorCountForDialog({ ...existing, status: DialogStatus.WAIT_USER });
      }

      set((state) => {
        const existingDetail = state.dialogDetails[dialogId];
        const updatedDetail = existingDetail
          ? {
              ...existingDetail,
              messages: mergeMessages(existingDetail.messages, [message]),
              last_message_at: message.created_at,
              status:
                DialogStatus.WAIT_USER,
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
                        DialogStatus.WAIT_USER,
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
      get().reconcileWaitingOperatorCountForDialog(dialog);
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
      get().reconcileWaitingOperatorCountForDialog(dialog);
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
      get().reconcileWaitingOperatorCountForDialog(dialog);
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
    const needsReconciliation = get().reconcileWaitingOperatorCountForDialog(dialog);
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
        dialogUpdateRevision: state.dialogUpdateRevision + 1,
        latestDialogUpdate: dialog,
      };
    });

    return needsReconciliation;
  },
  applyDialogUpdated: (dialog) => {
    const needsReconciliation = get().reconcileWaitingOperatorCountForDialog(dialog);
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
        dialogUpdateRevision: state.dialogUpdateRevision + 1,
        latestDialogUpdate: dialog,
      };
    });

    return needsReconciliation;
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
