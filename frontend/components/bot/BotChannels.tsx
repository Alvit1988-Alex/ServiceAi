"use client";

import { FormEvent, useEffect, useState } from "react";

import { listChannels, updateChannel } from "@/app/api/channelsApi";
import { BotChannel, ChannelType, VISIBLE_CHANNEL_TYPES } from "@/app/api/types";

import styles from "./BotChannels.module.css";

type ChannelConfigState = Record<string, unknown>;

interface ChannelFormState {
  config: ChannelConfigState;
  is_active: boolean;
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
  const [webchatCodes, setWebchatCodes] = useState<Record<number, string>>({});
  const [channelErrors, setChannelErrors] = useState<Record<number, string>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [successChannelId, setSuccessChannelId] = useState<number | null>(null);

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
          items.map((channel) => [channel.id, { config: buildConfigState(channel), is_active: channel.is_active }]),
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

  const handleActiveToggle = (channelId: number, isActive: boolean) => {
    setForms((prev) => ({
      ...prev,
      [channelId]: { ...prev[channelId], is_active: isActive },
    }));
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
        is_active: updatedChannel.is_active,
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
        is_active: form.is_active,
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

  const resolveWidgetScriptUrl = () => {
    if (typeof window !== "undefined") {
      return `${window.location.origin}/static/webchat.js`;
    }
    const rawBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
    if (rawBaseUrl) {
      let base = rawBaseUrl.replace(/\/$/, "");
      if (base.endsWith("/api")) {
        base = base.slice(0, -4);
      }
      return `${base}/static/webchat.js`;
    }
    return "/static/webchat.js";
  };

  const buildWebchatEmbedCode = (targetBotId: number) => {
    const scriptSrc = resolveWidgetScriptUrl();
    return `<script src=\"${scriptSrc}\" data-bot=\"${targetBotId}\"></script>`;
  };

  const handleCopyWebchatCode = async (channelId: number) => {
    const code = webchatCodes[channelId];
    if (!code || typeof navigator === "undefined" || !navigator.clipboard) {
      return;
    }

    try {
      await navigator.clipboard.writeText(code);
      setSuccessChannelId(channelId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось скопировать код";
      setChannelErrors((prev) => ({ ...prev, [channelId]: message }));
    }
  };

  const handleGenerateWebchatCode = (channelId: number) => {
    setWebchatCodes((prev) => ({ ...prev, [channelId]: buildWebchatEmbedCode(botId) }));
    setChannelErrors((prev) => ({ ...prev, [channelId]: "" }));
  };

  const renderWebchatSettings = (channel: BotChannel) => {
    const code = webchatCodes[channel.id] ?? "";

    return (
      <div className={styles.webchatSettings}>
        <p className={styles.subtitle}>
          Вставьте готовый сниппет на сайт, чтобы подключить Webchat.
        </p>
        <div className={styles.webchatCodeBlock}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => handleGenerateWebchatCode(channel.id)}
          >
            Получить код
          </button>
          <textarea
            className={styles.textarea}
            readOnly
            value={code}
            placeholder="Код будет доступен после нажатия кнопки"
            rows={8}
          />
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => handleCopyWebchatCode(channel.id)}
            disabled={!code}
          >
            Скопировать
          </button>
        </div>
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
        const form = forms[channel.id];
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
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={form?.is_active ?? false}
                  onChange={(event) => handleActiveToggle(channel.id, event.target.checked)}
                />
                <span>Активен</span>
              </label>
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
                конфигурации и включение/выключение.
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
