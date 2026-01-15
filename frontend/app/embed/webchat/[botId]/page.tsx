"use client";

import { CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

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
  webchat_config?: {
    name: string;
    theme: "light" | "dark" | "neutral";
    avatar_url?: string | null;
    avatar_data_url?: string | null;
    custom_colors_enabled: boolean;
    border_color: string | null;
    button_color: string | null;
    border_width: number;
  };
};

type InitErrorDetails = {
  url: string;
  status: number | null;
  hint: string;
};

function buildInitUrl(baseUrl: string): string {
  const normalized = baseUrl.replace(/\/$/, "");
  return `${normalized}/webchat/init`;
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
  const searchParams = useSearchParams();
  const botIdParam = typeof params?.botId === "string" ? params.botId : "";
  const botId = useMemo(() => {
    const parsed = Number(botIdParam);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }, [botIdParam]);
  const previewMode = searchParams.get("preview") === "1";

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
  const [uiCustomColorsEnabled, setUiCustomColorsEnabled] = useState(false);
  const [uiBorderColor, setUiBorderColor] = useState("#e6e8ef");
  const [uiButtonColor, setUiButtonColor] = useState("#2563eb");
  const [uiBorderWidth, setUiBorderWidth] = useState(1);
  const previewMessages = useMemo(
    () => [
      { id: "preview-1", sender: "user" as const, text: "Здравствуйте!" },
      {
        id: "preview-2",
        sender: "bot" as const,
        text: "Привет! Я помогу с вопросами. Напишите, что нужно.",
      },
      { id: "preview-3", sender: "user" as const, text: "Хочу понять, как работает сервис." },
      { id: "preview-4", sender: "bot" as const, text: "Просто задайте вопрос — я отвечу здесь." },
    ],
    [],
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!botId) {
      setError("Некорректный botId");
      return;
    }

    if (previewMode) {
      setMessages(previewMessages);
      setInputValue("");
      setSessionId(null);
      setWsUrl(null);
      setBotName(null);
      setError(null);
      setErrorDetails(null);
      setIsLoading(false);
      return;
    }

    const storageKey = `webchat_session_${botId}`;

    setIsLoading(true);
    setError(null);
    setErrorDetails(null);
    setMessages([]);

    const initUrl = buildInitUrl(API_BASE_URL);
    const errorHint = "Проверь nginx proxy для /api → backend";

    const initChat = async () => {
      const requestUrl = initUrl;
      try {
        const response = await fetch(requestUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ bot_id: botId }),
        });

        if (!response.ok) {
          setErrorDetails({ url: requestUrl, status: response.status, hint: errorHint });
          setError("Ошибка подключения");
          return;
        }

        const data = (await response.json()) as InitResponse;
        const nextSessionId = data.session_id || createId();
        setSessionId(nextSessionId);
        setWsUrl(data.ws_url);
        setBotName(data.bot.name);
        if (data.webchat_config) {
          const configTheme =
            data.webchat_config.theme === "dark" ||
            data.webchat_config.theme === "neutral" ||
            data.webchat_config.theme === "light"
              ? data.webchat_config.theme
              : "light";
          const avatarUrl =
            data.webchat_config.avatar_url ?? data.webchat_config.avatar_data_url ?? null;
          setUiName(data.webchat_config.name ?? "");
          setUiTheme(configTheme);
          if (avatarUrl) {
            const separator = avatarUrl.includes("?") ? "&" : "?";
            setUiAvatar(`${avatarUrl}${separator}v=${Date.now()}`);
          } else {
            setUiAvatar(null);
          }
          setUiCustomColorsEnabled(Boolean(data.webchat_config.custom_colors_enabled));
          setUiBorderColor(data.webchat_config.border_color ?? "#e6e8ef");
          setUiButtonColor(data.webchat_config.button_color ?? "#2563eb");
          setUiBorderWidth(
            Number.isFinite(Number(data.webchat_config.border_width))
              ? Number(data.webchat_config.border_width)
              : 1,
          );
        }
        if (typeof window !== "undefined") {
          window.sessionStorage.setItem(storageKey, nextSessionId);
        }
      } catch {
        setErrorDetails({ url: requestUrl, status: null, hint: errorHint });
        setError("Ошибка подключения");
      } finally {
        setIsLoading(false);
      }
    };

    initChat();
  }, [botId, previewMode, previewMessages]);

  useEffect(() => {
    if (!wsUrl || previewMode) {
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
  }, [wsUrl, previewMode]);

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
        avatarTransform?: { x: number; y: number; scale: number } | null;
        customColors?: {
          borderColor: string;
          buttonColor: string;
          borderWidth: number;
        } | null;
      };
      setUiName(payload.name ?? "");
      const nextTheme =
        payload.theme === "dark" || payload.theme === "neutral" || payload.theme === "light"
          ? payload.theme
          : "light";
      setUiTheme(nextTheme);
      setUiAvatar(payload.avatarDataUrl ?? null);
      if (payload.customColors) {
        setUiCustomColorsEnabled(true);
        setUiBorderColor(payload.customColors.borderColor);
        setUiButtonColor(payload.customColors.buttonColor);
        setUiBorderWidth(payload.customColors.borderWidth);
      } else {
        setUiCustomColorsEnabled(false);
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
    };
  }, []);

  const handleSend = () => {
    if (previewMode) return;
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
              <div>Hint: {errorDetails.hint}</div>
            </div>
          )}
        </div>
      </div>
    );
  }

  const resolvedName = uiName.trim() !== "" ? uiName : botName ?? "Webchat";
  const themeClass = styles[`theme${uiTheme.charAt(0).toUpperCase()}${uiTheme.slice(1)}`];
  const customStyles = uiCustomColorsEnabled
    ? ({
        "--frameBorderColor": uiBorderColor,
        "--frameBorderWidth": `${uiBorderWidth}px`,
        "--buttonBg": uiButtonColor,
      } as CSSProperties)
    : undefined;

  return (
    <div className={`${styles.container} ${themeClass}`} style={customStyles}>
      <header className={styles.header}>
        <div className={styles.headerMain}>
          {uiAvatar && (
            <div className={styles.avatar}>
              <img src={uiAvatar} alt="" />
            </div>
          )}
          <div className={styles.title}>{resolvedName}</div>
        </div>
        {!previewMode && isLoading && <div className={styles.status}>Подключение...</div>}
        {!previewMode && !isLoading && sessionId && (
          <div className={styles.status}>Сессия {sessionId.slice(0, 8)}</div>
        )}
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
          disabled={previewMode}
        />
        <button type="button" className={styles.sendButton} onClick={handleSend} disabled={previewMode}>
          Отправить
        </button>
      </div>
    </div>
  );
}
