"use client";

import { useEffect, useRef, useState } from "react";

import styles from "./DemoAiChat.module.css";

type ChatMessage = {
  id: string;
  sender: "user" | "bot";
  text: string;
};

const MAX_RECONNECT_ATTEMPTS = 2;

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const rand = Math.random() * 16;
    const value = char === "x" ? rand : (rand % 4) + 8;
    return Math.floor(value).toString(16);
  });
}

function resolveWsBaseUrl(): string {
  const rawApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (rawApiBase) {
    let base = rawApiBase.replace(/\/$/, "");
    if (base.endsWith("/api")) {
      base = base.slice(0, -4);
    }
    if (base.startsWith("https://")) {
      return `wss://${base.slice("https://".length)}`;
    }
    if (base.startsWith("http://")) {
      return `ws://${base.slice("http://".length)}`;
    }
    return base;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}`;
  }
  return "";
}

function extractMessageText(data: unknown): string | null {
  if (!data) return null;
  if (typeof data === "string") return data;
  if (typeof data === "object") {
    const record = data as Record<string, unknown>;
    const payload = record.payload as Record<string, unknown> | undefined;
    const nestedData = record.data as Record<string, unknown> | undefined;
    const nestedPayload = nestedData?.payload as Record<string, unknown> | undefined;
    return (
      (record.text as string | undefined) ??
      (payload?.text as string | undefined) ??
      (nestedData?.text as string | undefined) ??
      (nestedPayload?.text as string | undefined) ??
      null
    );
  }
  return null;
}

interface DemoAiChatProps {
  botId: number;
}

type ConnectionState = "connecting" | "open" | "error";

export default function DemoAiChat({ botId }: DemoAiChatProps) {
  const [sessionId] = useState(() => createSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const wsBase = resolveWsBaseUrl();
    if (!wsBase) {
      setConnectionState("error");
      return;
    }

    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;
      setConnectionState("connecting");
      const wsUrl = `${wsBase}/ws/webchat/${botId}/${sessionId}`;
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        if (!isMounted) return;
        reconnectAttempts.current = 0;
        setConnectionState("open");
      };

      socket.onmessage = (event) => {
        let parsed: unknown = null;
        try {
          parsed = JSON.parse(event.data);
        } catch {
          parsed = event.data;
        }
        const text = extractMessageText(parsed);
        if (!text) {
          if (process.env.NODE_ENV !== "production") {
            console.warn("Demo AI chat received unsupported message format");
          }
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            id: createSessionId(),
            sender: "bot",
            text,
          },
        ]);
      };

      socket.onerror = () => {
        if (!isMounted) return;
        setConnectionState("error");
        if (process.env.NODE_ENV !== "production") {
          console.warn("Demo AI chat socket error");
        }
      };

      socket.onclose = () => {
        if (!isMounted) return;
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          reconnectTimeout.current = setTimeout(connect, 1000 * reconnectAttempts.current);
        } else {
          setConnectionState("error");
        }
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      socketRef.current?.close();
    };
  }, [botId, sessionId]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text) return;
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      if (process.env.NODE_ENV !== "production") {
        console.warn("Demo AI chat socket is not connected");
      }
      return;
    }
    socket.send(JSON.stringify({ type: "user_message", text }));
    setMessages((prev) => [
      ...prev,
      {
        id: createSessionId(),
        sender: "user",
        text,
      },
    ]);
    setInputValue("");
  };

  const statusLabel =
    connectionState === "connecting"
      ? "Подключение..."
      : connectionState === "open"
        ? "Подключено"
        : "Ошибка подключения";

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Демо-диалог с ИИ</h2>
          <p className={styles.subtitle}>Проверьте ответы бота с текущими инструкциями и базой знаний.</p>
        </div>
        <span className={styles.status}>{statusLabel}</span>
      </header>

      <div className={styles.chatWindow}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>Сообщений пока нет.</div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`${styles.messageRow} ${
                message.sender === "user" ? styles.messageRowUser : styles.messageRowBot
              }`}
            >
              <div
                className={`${styles.messageBubble} ${
                  message.sender === "user" ? styles.messageBubbleUser : styles.messageBubbleBot
                }`}
              >
                {message.text}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputRow}>
        <input
          type="text"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              handleSend();
            }
          }}
          placeholder="Введите сообщение"
          className={styles.input}
        />
        <button type="button" onClick={handleSend} className={styles.sendButton}>
          Отправить
        </button>
      </div>
    </section>
  );
}
