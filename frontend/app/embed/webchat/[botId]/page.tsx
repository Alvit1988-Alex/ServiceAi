"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";

import { API_BASE_URL } from "@/app/api/config";
import { connect, disconnect, sendMessage } from "@/app/ws/webchat";

import styles from "./webchat.module.css";

type ChatMessage = {
  id: string;
  sender: "user" | "bot";
  text: string;
};

type InitResponse = {
  session_id: string;
  ws_url: string;
  bot: {
    id: number;
    name: string;
  };
};

type InitErrorDetails = {
  url: string;
  status?: number;
  message?: string;
};

function buildInitUrl(baseUrl: string): { primary: string; fallback?: string } {
  const normalized = baseUrl.replace(/\/$/, "");

  if (normalized.endsWith("/api")) {
    const withoutApi = normalized.slice(0, -4);
    const fallbackBase = withoutApi === "" ? "" : withoutApi;
    return {
      primary: `${normalized}/webchat/init`,
      fallback: `${fallbackBase}/webchat/init`,
    };
  }

  return {
    primary: `${normalized}/webchat/init`,
  };
}

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const rand = Math.random() * 16;
    const value = char === "x" ? rand : (rand % 4) + 8;
    return Math.floor(value).toString(16);
  });
}

function parseIncomingMessage(data: unknown): { sender: "user" | "bot"; text: string } | null {
  if (!data) return null;

  if (typeof data === "string") {
    return { sender: "bot", text: data };
  }

  if (typeof data === "object") {
    const record = data as Record<string, unknown>;
    const nested = record.data as Record<string, unknown> | undefined;
    const payload = record.payload as Record<string, unknown> | undefined;
    const nestedPayload = nested?.payload as Record<string, unknown> | undefined;

    const senderRaw = (nested?.sender ?? record.sender) as string | undefined;
    const sender = senderRaw === "user" ? "user" : "bot";
    const text =
      (nested?.text as string | undefined) ??
      (record.text as string | undefined) ??
      (nestedPayload?.text as string | undefined) ??
      (payload?.text as string | undefined);

    if (text) {
      return { sender, text };
    }
  }

  return null;
}

export default function EmbeddedWebchatPage() {
  const params = useParams();
  const botIdParam = typeof params?.botId === "string" ? params.botId : "";
  const botId = useMemo(() => {
    const parsed = Number(botIdParam);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }, [botIdParam]);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [wsUrl, setWsUrl] = useState<string | null>(null);
  const [botName, setBotName] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<InitErrorDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [uiName, setUiName] = useState("");
  const [uiTheme, setUiTheme] = useState<"light" | "dark" | "neutral">("light");
  const [uiAvatar, setUiAvatar] = useState<string | null>(null);
  const [uiAvatarTransform, setUiAvatarTransform] = useState<{
    x: number;
    y: number;
    scale: number;
  } | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!botId) {
      setError("Некорректный botId");
      return;
    }

    const storageKey = `webchat_session_${botId}`;

    setIsLoading(true);
    setError(null);
    setErrorDetails(null);

    const initUrls = buildInitUrl(API_BASE_URL);

    const initChat = async () => {
      let requestUrl = initUrls.primary;
      let initErrorDetails: InitErrorDetails | null = null;
      try {
        const response = await fetch(requestUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ bot_id: botId }),
        });

        let finalResponse = response;

        if (response.status === 404 && initUrls.fallback) {
          requestUrl = initUrls.fallback;
          finalResponse = await fetch(requestUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ bot_id: botId }),
          });
        }

        if (!finalResponse.ok) {
          initErrorDetails = { url: requestUrl, status: finalResponse.status };
          throw new Error("Init failed");
        }

        const data = (await finalResponse.json()) as InitResponse;
        const nextSessionId = data.session_id || createId();
        setSessionId(nextSessionId);
        setWsUrl(data.ws_url);
        setBotName(data.bot.name);
        if (typeof window !== "undefined") {
          window.sessionStorage.setItem(storageKey, nextSessionId);
        }
      } catch (caughtError) {
        if (!initErrorDetails) {
          initErrorDetails = {
            url: requestUrl,
            message: caughtError instanceof Error ? caughtError.message : "Unknown error",
          };
        }
        setErrorDetails(initErrorDetails);
        setError("Ошибка подключения");
      } finally {
        setIsLoading(false);
      }
    };

    initChat();
  }, [botId]);

  useEffect(() => {
    if (!wsUrl) {
      return;
    }

    connect(wsUrl, (data) => {
      const parsed = parseIncomingMessage(data);
      if (!parsed || parsed.sender === "user") {
        return;
      }
      setMessages((prev) => [...prev, { id: createId(), sender: parsed.sender, text: parsed.text }]);
    });

    return () => {
      disconnect();
    };
  }, [wsUrl]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const data = event.data as { type?: string; payload?: unknown } | null;
      if (!data || data.type !== "SERVICEAI_WEBCHAT_CONFIG" || !data.payload) {
        return;
      }
      const payload = data.payload as {
        name: string;
        theme: "light" | "dark" | "neutral";
        avatarDataUrl: string | null;
        avatarTransform: { x: number; y: number; scale: number } | null;
      };
      setUiName(payload.name ?? "");
      const nextTheme =
        payload.theme === "dark" || payload.theme === "neutral" || payload.theme === "light"
          ? payload.theme
          : "light";
      setUiTheme(nextTheme);
      setUiAvatar(payload.avatarDataUrl ?? null);
      setUiAvatarTransform(payload.avatarTransform ?? null);
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, []);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text) return;

    sendMessage(text);
    setMessages((prev) => [...prev, { id: createId(), sender: "user", text }]);
    setInputValue("");
  };

  if (error) {
    return (
      <div className={styles.errorState}>
        <div>
          <p>{error}</p>
          {errorDetails && (
            <div className={styles.errorDetails}>
              <div>URL: {errorDetails.url}</div>
              <div>Status: {errorDetails.status ?? "no response"}</div>
              <div>Hint: Проверь nginx proxy для /api → backend</div>
            </div>
          )}
        </div>
      </div>
    );
  }

  const resolvedName = uiName.trim() !== "" ? uiName : botName ?? "Webchat";
  const resolvedTransform = uiAvatarTransform ?? { x: 0, y: 0, scale: 1 };
  const themeClass = styles[`theme${uiTheme.charAt(0).toUpperCase()}${uiTheme.slice(1)}`];

  return (
    <div className={`${styles.container} ${themeClass}`}>
      <header className={styles.header}>
        <div className={styles.headerMain}>
          {uiAvatar && (
            <div className={styles.avatar}>
              <img
                src={uiAvatar}
                alt=""
                style={{
                  transform: `translate(calc(-50% + ${resolvedTransform.x}px), calc(-50% + ${resolvedTransform.y}px)) scale(${resolvedTransform.scale})`,
                }}
              />
            </div>
          )}
          <div className={styles.title}>{resolvedName}</div>
        </div>
        {isLoading && <div className={styles.status}>Подключение...</div>}
        {!isLoading && sessionId && <div className={styles.status}>Сессия {sessionId.slice(0, 8)}</div>}
      </header>
      <div className={styles.messages}>
        {messages.length === 0 ? (
          <div className={styles.empty}>Напишите первый вопрос — бот ответит здесь.</div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`${styles.message} ${
                message.sender === "user" ? styles.messageUser : styles.messageBot
              }`}
            >
              <span>{message.text}</span>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className={styles.inputBar}>
        <input
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              handleSend();
            }
          }}
          placeholder="Введите сообщение..."
          className={styles.input}
          type="text"
        />
        <button type="button" className={styles.sendButton} onClick={handleSend}>
          Отправить
        </button>
      </div>
    </div>
  );
}
