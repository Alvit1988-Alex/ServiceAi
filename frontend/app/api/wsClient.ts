"use client";

import { API_BASE_URL, buildWsUrl } from "./config";

export type DialogEventName =
  | "dialog_created"
  | "dialog_updated"
  | "dialog_locked"
  | "dialog_unlocked"
  | "message_created";

export interface DialogWsEvent {
  event: DialogEventName;
  data: unknown;
}

type Listener = (event: DialogWsEvent) => void;
type ConnectionListener = () => void;

export class AdminWebSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private connectionListeners = new Set<ConnectionListener>();
  private reconnectTimer: number | null = null;
  private token: string | null = null;
  private shouldReconnect = false;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  subscribeConnected(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    return () => this.connectionListeners.delete(listener);
  }

  connect(token: string) {
    if (!API_BASE_URL) {
      console.warn("API base URL is not configured for websocket connection");
      return;
    }

    this.disconnect();
    this.token = token;
    this.shouldReconnect = true;

    const url = buildWsUrl(`/ws/admin?token=${token}`);
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {
      if (this.socket !== socket || this.token !== token) {
        return;
      }

      this.connectionListeners.forEach((listener) => {
        try {
          listener();
        } catch (error) {
          console.error("Admin websocket connection listener failed", error);
        }
      });
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data) as DialogWsEvent;
        this.listeners.forEach((listener) => listener(payload));
      } catch (error) {
        console.error("Failed to parse websocket message", error);
      }
    };

    socket.onclose = () => {
      if (this.socket !== socket) {
        return;
      }

      this.socket = null;

      if (this.shouldReconnect && this.token === token) {
        this.scheduleReconnect();
      }
    };
    socket.onerror = () => {
      socket.close();
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    this.token = null;

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer || !this.token) {
      return;
    }

    this.reconnectTimer = window.setTimeout(() => {
      if (this.token) {
        this.connect(this.token);
      }
    }, 3000);
  }
}
