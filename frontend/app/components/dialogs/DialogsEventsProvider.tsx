"use client";

import {
  PropsWithChildren,
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from "react";

import { AdminWebSocketClient, DialogWsEvent } from "@/app/api/wsClient";
import { DialogDetail, DialogMessage, DialogShort } from "@/app/api/types";
import { useAuthStore } from "@/store/auth.store";
import { useDialogsStore } from "@/store/dialogs.store";

const DialogsWsContext = createContext<AdminWebSocketClient | null>(null);

function isDialogPayload(
  payload: unknown,
): payload is DialogDetail | DialogShort {
  if (!payload || typeof payload !== "object") {
    return false;
  }

  return "bot_id" in payload && "id" in payload;
}

function isMessagePayload(payload: unknown): payload is DialogMessage {
  if (!payload || typeof payload !== "object") {
    return false;
  }

  return "dialog_id" in payload && "id" in payload && "sender" in payload;
}

export function DialogsEventsProvider({ children }: PropsWithChildren) {
  // ВАЖНО: берём только нужные поля, а не весь auth-store
  const accessToken = useAuthStore((s) => s.accessToken);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // Гарантируем один и тот же экземпляр клиента
  const clientRef = useRef<AdminWebSocketClient | null>(null);
  if (!clientRef.current) {
    clientRef.current = new AdminWebSocketClient();
  }
  const client = clientRef.current;
  const reconciliationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconciliationInFlightRef = useRef(false);

  const scheduleCountReconciliation = useCallback(() => {
    if (reconciliationTimerRef.current) {
      clearTimeout(reconciliationTimerRef.current);
    }

    reconciliationTimerRef.current = setTimeout(() => {
      reconciliationTimerRef.current = null;
      if (reconciliationInFlightRef.current) {
        scheduleCountReconciliation();
        return;
      }

      reconciliationInFlightRef.current = true;
      void useDialogsStore
        .getState()
        .fetchWaitingOperatorCount()
        .catch((error) => {
          console.error("Failed to reconcile waiting operator dialogs count", error);
        })
        .finally(() => {
          reconciliationInFlightRef.current = false;
        });
    }, 200);
  }, []);

  // Подписка на события WS
  // Здесь НЕ используем useDialogsStore() – чтобы провайдер не подписывался на store.
  useEffect(() => {
    const unsubscribe = client.subscribe((event: DialogWsEvent) => {
      const {
        applyDialogCreated,
        applyDialogUpdated,
        applyDialogLocked,
        applyDialogUnlocked,
        applyMessageCreated,
      } = useDialogsStore.getState();

      const applyDialogEvent = (dialog: DialogDetail | DialogShort, apply: (value: DialogDetail | DialogShort) => void) => {
        const needsReconciliation = useDialogsStore.getState().reconcileWaitingOperatorCountForDialog(dialog);
        apply(dialog);
        if (needsReconciliation) {
          scheduleCountReconciliation();
        }
      };

      switch (event.event) {
        case "dialog_created": {
          if (isDialogPayload(event.data)) {
            applyDialogEvent(event.data, applyDialogCreated);
          }
          break;
        }
        case "dialog_updated": {
          if (isDialogPayload(event.data)) {
            applyDialogEvent(event.data, applyDialogUpdated);
          }
          break;
        }
        case "dialog_locked": {
          if (isDialogPayload(event.data)) {
            applyDialogEvent(event.data, applyDialogLocked);
          }
          break;
        }
        case "dialog_unlocked": {
          if (isDialogPayload(event.data)) {
            applyDialogEvent(event.data, applyDialogUnlocked);
          }
          break;
        }
        case "message_created": {
          if (isMessagePayload(event.data)) {
            applyMessageCreated(event.data);
          }
          break;
        }
        default:
          break;
      }
    });

    return () => {
      unsubscribe();
      if (reconciliationTimerRef.current) {
        clearTimeout(reconciliationTimerRef.current);
        reconciliationTimerRef.current = null;
      }
    };
  }, [client, scheduleCountReconciliation]);

  // Подключение / отключение WebSocket при изменении auth-состояния
  useEffect(() => {
    if (isAuthenticated && accessToken) {
      void useDialogsStore.getState().fetchWaitingOperatorCount().catch((error) => {
        console.error("Failed to fetch waiting operator dialogs count", error);
      });
      client.connect(accessToken);
      return () => client.disconnect();
    }

    client.disconnect();
    useDialogsStore.getState().resetWaitingOperatorCount();
    if (reconciliationTimerRef.current) {
      clearTimeout(reconciliationTimerRef.current);
      reconciliationTimerRef.current = null;
    }
    return () => client.disconnect();
  }, [accessToken, client, isAuthenticated]);

  return (
    <DialogsWsContext.Provider value={client}>
      {children}
    </DialogsWsContext.Provider>
  );
}

export function useDialogsWebSocket() {
  return useContext(DialogsWsContext);
}
