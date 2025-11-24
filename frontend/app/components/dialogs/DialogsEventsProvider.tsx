"use client";

import { PropsWithChildren, createContext, useContext, useEffect, useMemo } from "react";

import { AdminWebSocketClient, DialogWsEvent } from "@/app/api/wsClient";
import { DialogDetail, DialogMessage, DialogShort } from "@/app/api/types";
import { useAuthStore } from "@/store/auth.store";
import { useDialogsStore } from "@/store/dialogs.store";

const DialogsWsContext = createContext<AdminWebSocketClient | null>(null);

function isDialogPayload(payload: unknown): payload is DialogDetail | DialogShort {
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
  const { accessToken, isAuthenticated } = useAuthStore();
  const {
    applyDialogCreated,
    applyDialogUpdated,
    applyDialogLocked,
    applyDialogUnlocked,
    applyMessageCreated,
  } = useDialogsStore();

  const client = useMemo(() => new AdminWebSocketClient(), []);

  useEffect(() => {
    const unsubscribe = client.subscribe((event: DialogWsEvent) => {
      switch (event.event) {
        case "dialog_created": {
          if (isDialogPayload(event.data)) {
            applyDialogCreated(event.data);
          }
          break;
        }
        case "dialog_updated": {
          if (isDialogPayload(event.data)) {
            applyDialogUpdated(event.data);
          }
          break;
        }
        case "dialog_locked": {
          if (isDialogPayload(event.data)) {
            applyDialogLocked(event.data);
          }
          break;
        }
        case "dialog_unlocked": {
          if (isDialogPayload(event.data)) {
            applyDialogUnlocked(event.data);
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

    return unsubscribe;
  }, [
    applyDialogCreated,
    applyDialogLocked,
    applyDialogUnlocked,
    applyDialogUpdated,
    applyMessageCreated,
    client,
  ]);

  useEffect(() => {
    if (isAuthenticated && accessToken) {
      client.connect(accessToken);
      return () => client.disconnect();
    }

    client.disconnect();
    return () => client.disconnect();
  }, [accessToken, client, isAuthenticated]);

  return <DialogsWsContext.Provider value={client}>{children}</DialogsWsContext.Provider>;
}

export function useDialogsWebSocket() {
  return useContext(DialogsWsContext);
}
