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
  const countFetchInFlightRef = useRef(false);
  const countReconciliationPendingRef = useRef(false);
  const authStateRef = useRef({ isAuthenticated, accessToken });

  useEffect(() => {
    authStateRef.current = { isAuthenticated, accessToken };
  }, [accessToken, isAuthenticated]);

  const reconcileCountFromServer = useCallback(async () => {
    const authState = authStateRef.current;
    if (!authState.isAuthenticated || !authState.accessToken) {
      return;
    }

    if (countFetchInFlightRef.current) {
      countReconciliationPendingRef.current = true;
      return;
    }

    countFetchInFlightRef.current = true;
    try {
      do {
        countReconciliationPendingRef.current = false;
        const revisionBefore = useDialogsStore.getState().dialogUpdateRevision;
        await useDialogsStore.getState().fetchWaitingOperatorCount(() => {
          const currentAuth = authStateRef.current;
          return currentAuth.isAuthenticated && currentAuth.accessToken === authState.accessToken;
        });
        const revisionAfter = useDialogsStore.getState().dialogUpdateRevision;

        if (revisionAfter !== revisionBefore) {
          countReconciliationPendingRef.current = true;
        }
      } while (countReconciliationPendingRef.current && authStateRef.current.isAuthenticated);
    } catch (error) {
      console.error("Failed to reconcile waiting operator dialogs count", error);
    } finally {
      countFetchInFlightRef.current = false;
    }
  }, []);

  const scheduleCountReconciliation = useCallback(() => {
    if (reconciliationTimerRef.current) {
      clearTimeout(reconciliationTimerRef.current);
    }

    reconciliationTimerRef.current = setTimeout(() => {
      reconciliationTimerRef.current = null;
      void reconcileCountFromServer();
    }, 200);
  }, [reconcileCountFromServer]);

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

      const applyDialogEvent = (
        dialog: DialogDetail | DialogShort,
        apply: (value: DialogDetail | DialogShort) => boolean,
      ) => {
        const needsReconciliation = apply(dialog);
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

  useEffect(() => {
    return client.subscribeConnected(() => {
      void reconcileCountFromServer();
    });
  }, [client, reconcileCountFromServer]);

  // Подключение / отключение WebSocket при изменении auth-состояния
  useEffect(() => {
    if (isAuthenticated && accessToken) {
      client.connect(accessToken);
      return () => client.disconnect();
    }

    client.disconnect();
    useDialogsStore.getState().resetWaitingOperatorCount();
    countFetchInFlightRef.current = false;
    countReconciliationPendingRef.current = false;
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
