"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";

import { listChannels, updateChannel } from "@/app/api/channelsApi";
import { BotChannel, ChannelType, VISIBLE_CHANNEL_TYPES } from "@/app/api/types";

import styles from "./BotChannels.module.css";

type ChannelConfigState = Record<string, unknown>;

interface ChannelFormState {
  config: ChannelConfigState;
}

interface BotChannelsProps {
  botId: number;
}

interface ChannelField {
  key: string;
  label: string;
  placeholder?: string;
  type?: "text" | "textarea";
}

const CHANNEL_TYPE_LABELS: Partial<Record<ChannelType, string>> = {
  [ChannelType.TELEGRAM]: "Telegram",
  [ChannelType.AVITO]: "Avito",
  [ChannelType.MAX]: "Max",
  [ChannelType.WEBCHAT]: "Webchat",
};

const CHANNEL_INSTRUCTIONS: Partial<Record<ChannelType, { href: string; summary: string }>> = {
  [ChannelType.TELEGRAM]: {
    href: "/instructions/telegram.pdf",
    summary: "Как получить токен бота в BotFather и настроить webhook.",
  },
  [ChannelType.WEBCHAT]: {
    href: "/instructions/webchat.pdf",
    summary: "Как вставить код виджета чата на сайт.",
  },
  [ChannelType.AVITO]: {
    href: "/instructions/avito.pdf",
    summary: "Подключение Avito и настройка вебхука.",
  },
  [ChannelType.MAX]: {
    href: "/instructions/max.pdf",
    summary: "Подключение Max и настройка отправки сообщений.",
  },
};

const CHANNEL_FIELDS: Partial<Record<ChannelType, ChannelField[]>> = {
  [ChannelType.TELEGRAM]: [
    { key: "token", label: "API token", placeholder: "123456:ABC..." },
  ],
  [ChannelType.AVITO]: [
    { key: "client_id", label: "Client ID" },
    { key: "client_secret", label: "Client secret" },
    { key: "webhook_secret", label: "Webhook secret" },
    { key: "user_id", label: "User ID" },
  ],
  [ChannelType.MAX]: [
    { key: "send_message_url", label: "Send message URL" },
    { key: "api_base_url", label: "API base URL" },
    { key: "send_message_path", label: "Send message path" },
    { key: "auth_token", label: "Auth token" },
    { key: "token", label: "Token" },
    { key: "secret", label: "Webhook secret" },
  ],
  [ChannelType.WEBCHAT]: [],
};

function buildConfigState(channel: BotChannel): ChannelConfigState {
  const fields = CHANNEL_FIELDS[channel.channel_type] ?? [];
  const initialEntries: ChannelConfigState = { ...(channel.config ?? {}) };

  fields.forEach((field) => {
    const value = channel.config?.[field.key];
    if (value === undefined || value === null) {
      initialEntries[field.key] = "";
    }
  });

  if (channel.channel_type === ChannelType.AVITO) {
    if (initialEntries["reply_all_items"] === undefined) {
      initialEntries["reply_all_items"] = true;
    }
    if (!Array.isArray(initialEntries["allowed_item_ids"])) {
      initialEntries["allowed_item_ids"] = [];
    }
    if (initialEntries["user_id"] === undefined) {
      initialEntries["user_id"] = "";
    }
  }

  return initialEntries;
}

function parseConfigValue(key: string, value: unknown): unknown {
  if (typeof value !== "string") {
    return value;
  }

  const trimmed = value.trim();
  if (trimmed === "") {
    return undefined;
  }

  if (key === "extra_headers") {
    try {
      return JSON.parse(trimmed);
    } catch (error) {
      console.warn("Failed to parse extra_headers JSON", error);
      return trimmed;
    }
  }

  return trimmed;
}

function prepareConfig(config: ChannelConfigState): Record<string, unknown> {
  const prepared: Record<string, unknown> = {};
  Object.entries(config).forEach(([key, value]) => {
    const parsed = parseConfigValue(key, value);
    if (parsed !== undefined) {
      prepared[key] = parsed;
    }
  });
  return prepared;
}

export default function BotChannels({ botId }: BotChannelsProps) {
  const [channels, setChannels] = useState<BotChannel[]>([]);
  const [forms, setForms] = useState<Record<number, ChannelFormState>>({});
  const [allowedItemInputs, setAllowedItemInputs] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingChannelId, setSavingChannelId] = useState<number | null>(null);
  const [channelErrors, setChannelErrors] = useState<Record<number, string>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [successChannelId, setSuccessChannelId] = useState<number | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const modalIframeRef = useRef<HTMLIFrameElement | null>(null);
  const avatarInputRef = useRef<HTMLInputElement | null>(null);
  const [wcName, setWcName] = useState("");
  const [wcTheme, setWcTheme] = useState<"light" | "dark" | "neutral">("light");
  const [wcAvatar, setWcAvatar] = useState<string | null>(null);
  const [wcAvatarError, setWcAvatarError] = useState<string | null>(null);
  const [wcAvatarTransform, setWcAvatarTransform] = useState<{
    x: number;
    y: number;
    scale: number;
  } | null>({ x: 0, y: 0, scale: 1 });
  const [generatedCode, setGeneratedCode] = useState<string>("");
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const avatarDragRef = useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setLoadError(null);
    setSuccessChannelId(null);
    setChannelErrors({});

    listChannels(botId)
      .then((items) => {
        if (!isMounted) return;
        setChannels(items);
        const nextForms = Object.fromEntries(
          items.map((channel) => [channel.id, { config: buildConfigState(channel) }]),
        );
        setForms(nextForms);
        setAllowedItemInputs({});
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        const message = err instanceof Error ? err.message : "Не удалось загрузить каналы";
        setLoadError(message);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [botId]);

  const handleConfigChange = (channelId: number, key: string, value: string) => {
    setForms((prev) => ({
      ...prev,
      [channelId]: {
        ...prev[channelId],
        config: { ...prev[channelId]?.config, [key]: value },
      },
    }));
  };

  const handleReplyAllToggle = (channelId: number, replyAll: boolean) => {
    setForms((prev) => ({
      ...prev,
      [channelId]: {
        ...prev[channelId],
        config: { ...prev[channelId]?.config, reply_all_items: replyAll },
      },
    }));
  };

  const handleAllowedItemInputChange = (channelId: number, value: string) => {
    setAllowedItemInputs((prev) => ({ ...prev, [channelId]: value }));
  };

  const handleAddAllowedItem = (channelId: number) => {
    const value = (allowedItemInputs[channelId] ?? "").trim();
    if (!value) return;

    setForms((prev) => {
      const allowedRaw = prev[channelId]?.config?.["allowed_item_ids"];
      const currentAllowed = Array.isArray(allowedRaw)
        ? [...(allowedRaw as unknown[])]
        : [];

      if (currentAllowed.includes(value)) {
        return prev;
      }

      return {
        ...prev,
        [channelId]: {
          ...prev[channelId],
          config: { ...prev[channelId]?.config, allowed_item_ids: [...currentAllowed, value] },
        },
      };
    });

    setAllowedItemInputs((prev) => ({ ...prev, [channelId]: "" }));
  };

  const handleRemoveAllowedItem = (channelId: number, itemId: string) => {
    setForms((prev) => {
      const allowedRaw = prev[channelId]?.config?.["allowed_item_ids"];
      const currentAllowed = Array.isArray(allowedRaw)
        ? (allowedRaw as unknown[])
        : [];
      const nextAllowed = currentAllowed.filter((item) => String(item) !== itemId);

      return {
        ...prev,
        [channelId]: {
          ...prev[channelId],
          config: { ...prev[channelId]?.config, allowed_item_ids: nextAllowed },
        },
      };
    });
  };

  const INTERNAL_KEYS = new Set(["secret_token", "webhook_status", "webhook_error", "secret"]);
  const AVITO_HIDDEN_KEYS = new Set([
    "send_message_url",
    "api_base_url",
    "send_message_path",
    "token",
  ]);

  const applyChannelUpdate = (channelId: number, updatedChannel: BotChannel) => {
    syncChannelState(channelId, updatedChannel);
    setSuccessChannelId(channelId);
  };

  const syncChannelState = (channelId: number, updatedChannel: BotChannel) => {
    setChannels((prev) => prev.map((item) => (item.id === channelId ? updatedChannel : item)));
    setForms((prev) => ({
      ...prev,
      [channelId]: {
        config: buildConfigState(updatedChannel),
      },
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>, channelId: number) => {
    event.preventDefault();
    const form = forms[channelId];
    if (!form) {
      return;
    }

    setSavingChannelId(channelId);
    setChannelErrors((prev) => ({ ...prev, [channelId]: "" }));
    setSuccessChannelId(null);

    try {
      const payload = {
        config: prepareConfig(form.config),
      };
      const updatedChannel = await updateChannel(botId, channelId, payload);
      applyChannelUpdate(channelId, updatedChannel);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось обновить канал";
      setChannelErrors((prev) => ({ ...prev, [channelId]: message }));
    } finally {
      setSavingChannelId(null);
    }
  };

  const renderAvitoFilters = (channel: BotChannel) => {
    const form = forms[channel.id];
    if (!form) return null;

    const replyAllRaw = form.config["reply_all_items"];
    const replyAll = typeof replyAllRaw === "boolean" ? replyAllRaw : true;
    const allowedRaw = form.config["allowed_item_ids"];
    const allowedItems = Array.isArray(allowedRaw)
      ? (allowedRaw as unknown[]).map((value) => String(value))
      : [];
    const inputValue = allowedItemInputs[channel.id] ?? "";

    return (
      <div className={styles.field}>
        <label className={styles.switch}>
          <input
            type="checkbox"
            checked={replyAll}
            onChange={(event) => handleReplyAllToggle(channel.id, event.target.checked)}
          />
          <span>Отвечать на все объявления</span>
        </label>

        {!replyAll && (
          <>
            <span className={styles.fieldLabel}>ID объявления</span>
            <div className={styles.inlineInputs}>
              <input
                className={styles.input}
                type="text"
                value={inputValue}
                onChange={(event) => handleAllowedItemInputChange(channel.id, event.target.value)}
                placeholder="123456789"
              />
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => handleAddAllowedItem(channel.id)}
              >
                Добавить
              </button>
            </div>
            <p className={styles.helperText}>Добавьте один или несколько ID объявлений для ответа бота.</p>
            <ul className={styles.tagList}>
              {allowedItems.map((item) => (
                <li key={item} className={styles.tag}>
                  <span>{item}</span>
                  <button
                    type="button"
                    className={styles.tagRemoveButton}
                    onClick={() => handleRemoveAllowedItem(channel.id, item)}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    );
  };

  const renderFields = (channel: BotChannel) => {
    const form = forms[channel.id];
    if (!form) return null;

    const definedFields = CHANNEL_FIELDS[channel.channel_type] ?? [];
    const existingKeys = new Set(definedFields.map((field) => field.key));
    const additionalKeys = Object.keys(form.config)
      .filter((key) => !existingKeys.has(key))
      .filter((key) => !INTERNAL_KEYS.has(key))
      .filter(
        (key) =>
          !(
            channel.channel_type === ChannelType.AVITO &&
            (key === "reply_all_items" || key === "allowed_item_ids" || AVITO_HIDDEN_KEYS.has(key))
          ),
      );

    return (
      <div className={styles.fieldsGrid}>
        {definedFields.map((field) => (
          <label key={field.key} className={styles.field}>
            <span className={styles.fieldLabel}>{field.label}</span>
            {field.type === "textarea" ? (
              <textarea
                className={styles.textarea}
                value={String(form.config[field.key] ?? "")}
                onChange={(event) => handleConfigChange(channel.id, field.key, event.target.value)}
                placeholder={field.placeholder}
                rows={3}
              />
            ) : (
              <input
                className={styles.input}
                type="text"
                value={String(form.config[field.key] ?? "")}
                onChange={(event) => handleConfigChange(channel.id, field.key, event.target.value)}
                placeholder={field.placeholder}
              />
            )}
          </label>
        ))}

        {additionalKeys.map((key) => (
          <label key={key} className={styles.field}>
            <span className={styles.fieldLabel}>{key}</span>
            <input
              className={styles.input}
              type="text"
              value={String(form.config[key] ?? "")}
              onChange={(event) => handleConfigChange(channel.id, key, event.target.value)}
            />
          </label>
        ))}

        {channel.channel_type === ChannelType.AVITO && renderAvitoFilters(channel)}
      </div>
    );
  };

  const clampValue = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

  const sendWebchatConfig = () => {
    const targets = [iframeRef.current?.contentWindow, modalIframeRef.current?.contentWindow].filter(
      Boolean,
    ) as Window[];
    if (targets.length === 0) return;
    const resolvedTransform = wcAvatarTransform ?? { x: 0, y: 0, scale: 1 };
    targets.forEach((targetWindow) => {
      targetWindow.postMessage(
        {
          type: "SERVICEAI_WEBCHAT_CONFIG",
          payload: {
            name: wcName,
            theme: wcTheme,
            avatarDataUrl: wcAvatar,
            avatarTransform: wcAvatar ? resolvedTransform : null,
          },
        },
        "*",
      );
    });
  };

  useEffect(() => {
    sendWebchatConfig();
  }, [wcName, wcTheme, wcAvatar, wcAvatarTransform]);

  useEffect(() => {
    function handleMouseMove(this: Window, event: globalThis.MouseEvent) {
      if (!avatarDragRef.current) return;
      const { startX, startY, originX, originY } = avatarDragRef.current;
      const scale = wcAvatarTransform?.scale ?? 1;
      const limit = 80 * scale;
      const nextX = clampValue(originX + (event.clientX - startX), -limit, limit);
      const nextY = clampValue(originY + (event.clientY - startY), -limit, limit);
      if (Math.abs(event.clientX - startX) > 3 || Math.abs(event.clientY - startY) > 3) {
        avatarDragRef.current.moved = true;
      }
      setWcAvatarTransform((prev) => ({
        x: nextX,
        y: nextY,
        scale: prev?.scale ?? 1,
      }));
    }

    function handleMouseUp(this: Window) {
      avatarDragRef.current = null;
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [wcAvatarTransform]);

  const renderWebchatSettings = (channel: BotChannel) => {
    const MAX_AVATAR_SIZE = 2 * 1024 * 1024;

    const handleAvatarUpload = (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      if (file.size > MAX_AVATAR_SIZE) {
        setWcAvatarError("Файл слишком большой. Максимум 2 МБ.");
        event.target.value = "";
        return;
      }

      setWcAvatarError(null);
      const imageUrl = URL.createObjectURL(file);
      const image = new Image();

      image.onload = () => {
        const maxSide = Math.max(image.width, image.height);
        const scale = maxSide > 1024 ? 1024 / maxSide : 1;
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(image.width * scale);
        canvas.height = Math.round(image.height * scale);
        const context = canvas.getContext("2d");
        if (!context) {
          URL.revokeObjectURL(imageUrl);
          return;
        }
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        setWcAvatar(dataUrl);
        setWcAvatarTransform({ x: 0, y: 0, scale: 1 });
        URL.revokeObjectURL(imageUrl);
        event.target.value = "";
      };

      image.onerror = () => {
        URL.revokeObjectURL(imageUrl);
        setWcAvatarError("Не удалось прочитать файл.");
      };

      image.src = imageUrl;
    };

    const handleAvatarMouseDown = (event: ReactMouseEvent<HTMLDivElement>) => {
      if (!wcAvatar || !wcAvatarTransform) return;
      event.preventDefault();
      avatarDragRef.current = {
        startX: event.clientX,
        startY: event.clientY,
        originX: wcAvatarTransform.x,
        originY: wcAvatarTransform.y,
        moved: false,
      };
    };

    const handleGenerate = () => {
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      const resolvedTransform = wcAvatarTransform ?? { x: 0, y: 0, scale: 1 };
      const dataAvatar = wcAvatar ?? "";
      const dataX = wcAvatar ? String(resolvedTransform.x) : "0";
      const dataY = wcAvatar ? String(resolvedTransform.y) : "0";
      const dataScale = wcAvatar ? String(resolvedTransform.scale) : "1";

      setGeneratedCode(
        `<script
  src="${origin}/static/webchat.js"
  data-bot="${channel.bot_id}"
  data-theme="${wcTheme}"
  data-name="${wcName}"
  data-avatar="${dataAvatar}"
  data-avatar-x="${dataX}"
  data-avatar-y="${dataY}"
  data-avatar-scale="${dataScale}">
</script>`,
      );
    };

    const displayTransform = wcAvatarTransform ?? { x: 0, y: 0, scale: 1 };
    const themeGroupName = `webchat-theme-${channel.id}`;

    return (
      <div className={styles.webchatLayout}>
        <div className={styles.webchatSettings}>
          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor={`webchat-name-${channel.id}`}>
              Имя
            </label>
            <input
              id={`webchat-name-${channel.id}`}
              type="text"
              className={styles.input}
              placeholder="Имя в чате"
              value={wcName}
              onChange={(event) => setWcName(event.target.value)}
            />
          </div>

          <div className={styles.field}>
            <span className={styles.fieldLabel}>Тема</span>
            <div className={styles.inlineInputs}>
              {(["light", "dark", "neutral"] as const).map((theme) => (
                <label key={theme} className={styles.switch}>
                  <input
                    type="radio"
                    name={themeGroupName}
                    value={theme}
                    checked={wcTheme === theme}
                    onChange={() => setWcTheme(theme)}
                  />
                  <span>{theme}</span>
                </label>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <span className={styles.fieldLabel}>Аватар</span>
            <input
              ref={avatarInputRef}
              id={`webchat-avatar-${channel.id}`}
              type="file"
              accept="image/*"
              className={styles.hiddenFileInput}
              onChange={handleAvatarUpload}
            />
          </div>

          <div className={styles.field}>
            <span className={styles.fieldLabel}>Редактор аватара</span>
            <div
              className={styles.avatarEditor}
              onMouseDown={handleAvatarMouseDown}
              onClick={() => {
                if (avatarDragRef.current?.moved) {
                  avatarDragRef.current.moved = false;
                  return;
                }
                avatarInputRef.current?.click();
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  avatarInputRef.current?.click();
                }
              }}
            >
              {wcAvatar ? (
                <img
                  src={wcAvatar}
                  alt="Avatar preview"
                  style={{
                    transform: `translate(calc(-50% + ${displayTransform.x}px), calc(-50% + ${displayTransform.y}px)) scale(${displayTransform.scale})`,
                  }}
                />
              ) : (
                <span className={styles.avatarPlaceholder}>+</span>
              )}
            </div>
            {wcAvatarError && <span className={styles.error}>{wcAvatarError}</span>}
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor={`webchat-scale-${channel.id}`}>
              Масштаб
            </label>
            <input
              id={`webchat-scale-${channel.id}`}
              type="range"
              min={1}
              max={3}
              step={0.01}
              value={displayTransform.scale}
              onChange={(event) => {
                const nextScale = Number(event.target.value);
                setWcAvatarTransform((prev) => ({
                  x: prev?.x ?? 0,
                  y: prev?.y ?? 0,
                  scale: nextScale,
                }));
              }}
            />
          </div>

          <div className={styles.inlineInputs}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => {
                setWcAvatarTransform({ x: 0, y: 0, scale: 1 });
                setWcAvatarError(null);
              }}
            >
              Сброс
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => {
                setWcAvatar(null);
                setWcAvatarTransform(null);
                setWcAvatarError(null);
              }}
            >
              Удалить
            </button>
          </div>

          <div className={styles.webchatCodeBlock}>
            <button type="button" className={styles.secondaryButton} onClick={handleGenerate}>
              Сгенерировать
            </button>
            {generatedCode && (
              <textarea
                className={styles.textarea}
                readOnly
                value={generatedCode}
                rows={8}
              />
            )}
          </div>
        </div>
        <div className={styles.webchatPreview}>
          <iframe
            ref={iframeRef}
            src={`/embed/webchat/${channel.bot_id}?preview=1`}
            title="Webchat preview"
            onLoad={sendWebchatConfig}
            className={styles.webchatPreviewFrame}
            style={{
              width: "100%",
              height: "520px",
              border: "1px solid #e5e7eb",
              borderRadius: "16px",
            }}
          />
          <button
            type="button"
            className={styles.previewButton}
            onClick={() => setIsPreviewOpen(true)}
          >
            Посмотреть превью
          </button>
        </div>
        {isPreviewOpen && (
          <div className={styles.previewOverlay}>
            <div className={styles.previewModal}>
              <div className={styles.previewHeader}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => setIsPreviewOpen(false)}
                >
                  Назад
                </button>
              </div>
              <iframe
                ref={modalIframeRef}
                src={`/embed/webchat/${channel.bot_id}?preview=1`}
                title="Webchat preview full"
                onLoad={sendWebchatConfig}
                className={styles.previewIframe}
              />
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderWebhookStatus = (channel: BotChannel) => {
    if (channel.channel_type !== ChannelType.TELEGRAM) {
      return null;
    }

    const status = channel.webhook_status;
    const error = channel.webhook_error;

    if (!status && !error) {
      return null;
    }

    return (
      <div className={styles.webhookStatus}>
        {status && (
          <div className={styles.webhookStatusLine}>
            <span className={styles.webhookStatusLabel}>Статус вебхука:</span>
            <span className={styles.webhookStatusValue}>{status}</span>
          </div>
        )}
        {error && <div className={styles.webhookStatusError}>{error}</div>}
      </div>
    );
  };

  const visibleChannels = channels.filter((channel) =>
    VISIBLE_CHANNEL_TYPES.includes(channel.channel_type),
  );

  return (
    <section className={styles.section}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>Каналы связи</h3>
          <p className={styles.subtitle}>
            Настройте токены и вебхуки для каждого подключенного канала. Пустые поля не будут отправлены
            при сохранении.
          </p>
        </div>
      </header>

      {loading && <p className={styles.muted}>Загружаем каналы...</p>}
      {!loading && loadError && <p className={styles.error}>{loadError}</p>}
      {!loading && !loadError && visibleChannels.length === 0 && (
        <p className={styles.muted}>Нет доступных каналов для отображения.</p>
      )}

      {!loading && !loadError && visibleChannels.map((channel) => {
        const instruction = CHANNEL_INSTRUCTIONS[channel.channel_type];
        const channelLabel = CHANNEL_TYPE_LABELS[channel.channel_type] ?? channel.channel_type;
        const channelError = channelErrors[channel.id];
        return (
          <form
            key={channel.id}
            className={styles.card}
            onSubmit={(event) => handleSubmit(event, channel.id)}
          >
            <div className={styles.cardHeader}>
              <div>
                <div className={styles.badge}>{channelLabel}</div>
                <div className={styles.channelMeta}>ID: {channel.id}</div>
              </div>
            </div>

            {channel.channel_type === ChannelType.WEBCHAT
              ? renderWebchatSettings(channel)
              : renderFields(channel)}

            {renderWebhookStatus(channel)}

            <div className={styles.actions}>
              {successChannelId === channel.id && (
                <span className={styles.success}>Настройки сохранены</span>
              )}
              {channelError && <span className={styles.error}>{channelError}</span>}
              {instruction && (
                <a
                  href={instruction.href}
                  className={styles.instructionLink}
                  download
                  title={instruction.summary}
                >
                  Инструкция
                </a>
              )}
              <span className={styles.actionHint}>
                Тестирование канала будет добавлено позже. Сейчас доступно только сохранение
                конфигурации.
              </span>
              <button
                type="button"
                className={styles.secondaryButton}
                disabled
                title="Тестирование канала скоро будет доступно."
              >
                Скоро
              </button>
              <button
                type="submit"
                className={styles.saveButton}
                disabled={savingChannelId === channel.id}
              >
                {savingChannelId === channel.id ? "Сохраняем..." : "Сохранить"}
              </button>
            </div>
          </form>
        );
      })}
    </section>
  );
}
