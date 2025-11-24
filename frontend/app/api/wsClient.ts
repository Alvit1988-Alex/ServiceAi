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

export class AdminWebSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private reconnectTimer: number | null = null;
  private token: string | null = null;

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  connect(token: string) {
    if (!API_BASE_URL) {
      console.warn("API base URL is not configured for websocket connection");
      return;
    }

    this.token = token;
    this.disconnect();

    const url = buildWsUrl(`/ws/admin?token=${token}`);
    this.socket = new WebSocket(url);

    this.socket.onmessage = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data) as DialogWsEvent;
        this.listeners.forEach((listener) => listener(payload));
      } catch (error) {
        console.error("Failed to parse websocket message", error);
      }
    };

    this.socket.onclose = () => {
      if (this.token) {
        this.scheduleReconnect();
      }
    };
    this.socket.onerror = () => {
      this.disconnect();
    };
  }

  disconnect() {
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
