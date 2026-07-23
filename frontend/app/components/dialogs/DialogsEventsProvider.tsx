"use client";

import {
  PropsWithChildren,
  createContext,
  useContext,
  useCallback,
  useEffect,
  useRef,
} from "react";

import { AdminWebSocketClient, DialogWsEvent } from "@/app/api/wsClient";
import { DialogDetail, DialogMessage, DialogShort } from "@/app/api/types";
import { useAuthStore } from "@/store/auth.store";
import { useDialogsStore } from "@/store/dialogs.store";

const DialogsWsContext = createContext<AdminWebSocketClient | null>(null);

interface CountReconciliationRunState {
  generation: number;
  inFlight: boolean;
  pending: boolean;
}

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
  const authStateRef = useRef({ isAuthenticated, accessToken });
  const authGenerationRef = useRef(0);
  const authKeyRef = useRef<string | null>(null);
  const countRunStateRef = useRef<CountReconciliationRunState>({
    generation: 0,
    inFlight: false,
    pending: false,
  });
  const authKey = isAuthenticated && accessToken ? accessToken : null;

  useEffect(() => {
    authStateRef.current = { isAuthenticated, accessToken };

    if (authKeyRef.current !== authKey) {
      authKeyRef.current = authKey;
      authGenerationRef.current += 1;
      countRunStateRef.current = {
        generation: authGenerationRef.current,
        inFlight: false,
        pending: false,
      };

      if (reconciliationTimerRef.current) {
        clearTimeout(reconciliationTimerRef.current);
        reconciliationTimerRef.current = null;
      }
    }
  }, [accessToken, authKey, isAuthenticated]);

  const reconcileCountFromServer = useCallback(async () => {
    const initialAuth = authStateRef.current;
    const initialGeneration = authGenerationRef.current;
    if (!initialAuth.isAuthenticated || !initialAuth.accessToken) {
      return;
    }

    if (countRunStateRef.current.generation !== initialGeneration) {
      countRunStateRef.current = {
        generation: initialGeneration,
        inFlight: false,
        pending: false,
      };
    }

    if (countRunStateRef.current.inFlight) {
      countRunStateRef.current = { ...countRunStateRef.current, pending: true };
      return;
    }

    countRunStateRef.current = {
      generation: initialGeneration,
      inFlight: true,
      pending: false,
    };

    try {
      while (true) {
        const currentAuth = authStateRef.current;
        const requestGeneration = authGenerationRef.current;
        const requestToken = currentAuth.accessToken;

        if (
          requestGeneration !== initialGeneration ||
          !currentAuth.isAuthenticated ||
          !requestToken ||
          countRunStateRef.current.generation !== initialGeneration
        ) {
          return;
        }

        countRunStateRef.current = { ...countRunStateRef.current, pending: false };
        const revisionBefore = useDialogsStore.getState().dialogUpdateRevision;
        const isCurrentRequest = () => {
          const latestAuth = authStateRef.current;
          return (
            latestAuth.isAuthenticated &&
            latestAuth.accessToken === requestToken &&
            authGenerationRef.current === requestGeneration &&
            countRunStateRef.current.generation === requestGeneration
          );
        };

        const applied = await useDialogsStore.getState().fetchWaitingOperatorCount(isCurrentRequest);

        if (!applied || !isCurrentRequest()) {
          return;
        }

        const revisionAfter = useDialogsStore.getState().dialogUpdateRevision;
        if (revisionAfter !== revisionBefore && countRunStateRef.current.generation === requestGeneration) {
          countRunStateRef.current = { ...countRunStateRef.current, pending: true };
        }

        if (!countRunStateRef.current.pending) {
          return;
        }
      }
    } catch (error) {
      console.error("Failed to reconcile waiting operator dialogs count", error);
    } finally {
      if (countRunStateRef.current.generation === initialGeneration) {
        countRunStateRef.current = { ...countRunStateRef.current, inFlight: false };
      }
    }
  }, []);

  const scheduleCountReconciliation = useCallback(() => {
    if (reconciliationTimerRef.current) {
      clearTimeout(reconciliationTimerRef.current);
    }

    const scheduledGeneration = authGenerationRef.current;
    reconciliationTimerRef.current = setTimeout(() => {
      reconciliationTimerRef.current = null;
      if (authGenerationRef.current !== scheduledGeneration) {
        return;
      }

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
    countRunStateRef.current = {
      generation: authGenerationRef.current,
      inFlight: false,
      pending: false,
    };
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
