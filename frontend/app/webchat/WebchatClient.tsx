"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { buildWsUrl } from "@/app/api/config";

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

export default function WebchatClient() {
  const searchParams = useSearchParams();
  const botIdParam = searchParams.get("bot_id")?.trim() ?? "";
  const botId = useMemo(() => {
    const parsed = Number(botIdParam);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }, [botIdParam]);

  const [sessionId] = useState(() => createSessionId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [connectionState, setConnectionState] = useState<"idle" | "connecting" | "open" | "closed">(
    "idle"
  );
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!botId) {
      return;
    }

    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;
      setConnectionState("connecting");
      const wsUrl = buildWsUrl(`/ws/webchat/${botId}/${sessionId}`);
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
            console.warn("Webchat received unsupported message format");
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
        if (process.env.NODE_ENV !== "production") {
          console.warn("Webchat socket error");
        }
      };

      socket.onclose = () => {
        if (!isMounted) return;
        setConnectionState("closed");
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          reconnectTimeout.current = setTimeout(connect, 1000 * reconnectAttempts.current);
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
    if (!inputValue.trim()) return;
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      if (process.env.NODE_ENV !== "production") {
        console.warn("Webchat socket is not connected");
      }
      return;
    }
    const text = inputValue.trim();
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

  if (!botId) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 p-6 text-gray-800">
        <div className="max-w-md rounded-lg border border-gray-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-semibold">Webchat недоступен</h1>
          <p className="mt-2 text-sm text-gray-600">Не передан или некорректен параметр bot_id.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="flex w-full max-w-xl flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <header className="border-b border-gray-200 px-4 py-3 text-sm text-gray-600">
          Webchat · Bot #{botId}
          {connectionState !== "open" && (
            <span className="ml-2 text-xs text-amber-600">Соединение: {connectionState}</span>
          )}
        </header>
        <section className="flex max-h-[60vh] flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
            <div className="text-center text-sm text-gray-500">Сообщений пока нет.</div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                    message.sender === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {message.text}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </section>
        <footer className="border-t border-gray-200 p-3">
          <div className="flex gap-2">
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
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            <button
              type="button"
              onClick={handleSend}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Отправить
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}
