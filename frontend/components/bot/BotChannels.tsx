"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { createChannel, listChannels, updateChannel } from "@/app/api/channelsApi";
import { BotChannel, ChannelType } from "@/app/api/types";

import styles from "./BotChannels.module.css";

type ChannelConfigState = Record<string, string>;

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

const CHANNEL_TYPE_LABELS: Record<ChannelType, string> = {
  [ChannelType.TELEGRAM]: "Telegram",
  [ChannelType.WHATSAPP_GREEN]: "WhatsApp Green API",
  [ChannelType.WHATSAPP_360]: "WhatsApp 360dialog",
  [ChannelType.WHATSAPP_CUSTOM]: "WhatsApp Custom",
  [ChannelType.AVITO]: "Avito",
  [ChannelType.MAX]: "Max",
  [ChannelType.WEBCHAT]: "Webchat",
};

const CHANNEL_FIELDS: Record<ChannelType, ChannelField[]> = {
  [ChannelType.TELEGRAM]: [
    { key: "token", label: "API token", placeholder: "123456:ABC..." },
    { key: "secret_token", label: "Секретный токен" },
  ],
  [ChannelType.WHATSAPP_GREEN]: [
    { key: "send_message_url", label: "Send message URL" },
    { key: "api_base_url", label: "API base URL" },
    { key: "send_message_path", label: "Send message path" },
    { key: "instance_id", label: "Instance ID" },
    { key: "api_token", label: "API token" },
    { key: "secret", label: "Webhook secret" },
    { key: "webhook_secret", label: "Webhook secret (альт.)" },
  ],
  [ChannelType.WHATSAPP_360]: [
    { key: "send_message_url", label: "Send message URL" },
    { key: "api_base_url", label: "API base URL" },
    { key: "send_message_path", label: "Send message path" },
    { key: "auth_token", label: "Auth token" },
    { key: "secret", label: "Webhook secret" },
    { key: "webhook_secret", label: "Webhook secret (альт.)" },
  ],
  [ChannelType.WHATSAPP_CUSTOM]: [
    { key: "send_message_url", label: "Send message URL" },
    { key: "auth_token", label: "Auth token" },
    { key: "token", label: "Token" },
    { key: "secret", label: "Webhook secret" },
    { key: "webhook_secret", label: "Webhook secret (альт.)" },
    { key: "api_key_header", label: "API key header" },
    { key: "api_key", label: "API key" },
    {
      key: "extra_headers",
      label: "Дополнительные заголовки (JSON)",
      type: "textarea",
      placeholder: '{"X-Header": "value"}',
    },
  ],
  [ChannelType.AVITO]: [
    { key: "send_message_url", label: "Send message URL" },
    { key: "api_base_url", label: "API base URL" },
    { key: "send_message_path", label: "Send message path" },
    { key: "auth_token", label: "Auth token" },
    { key: "token", label: "Token" },
    { key: "secret", label: "Webhook secret" },
  ],
  [ChannelType.MAX]: [
    { key: "send_message_url", label: "Send message URL" },
    { key: "api_base_url", label: "API base URL" },
    { key: "send_message_path", label: "Send message path" },
    { key: "auth_token", label: "Auth token" },
    { key: "token", label: "Token" },
    { key: "secret", label: "Webhook secret" },
  ],
  [ChannelType.WEBCHAT]: [
    { key: "token", label: "Token" },
    { key: "secret", label: "Webhook secret" },
  ],
};

function buildConfigState(channel: BotChannel): ChannelConfigState {
  const fields = CHANNEL_FIELDS[channel.channel_type] ?? [];
  const initialEntries: ChannelConfigState = {};

  fields.forEach((field) => {
    const value = channel.config?.[field.key];
    initialEntries[field.key] = value === undefined || value === null ? "" : String(value);
  });

  Object.entries(channel.config ?? {}).forEach(([key, value]) => {
    if (!(key in initialEntries)) {
      initialEntries[key] = value === undefined || value === null ? "" : String(value);
    }
  });

  return initialEntries;
}

function parseConfigValue(key: string, value: string): unknown {
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
  const [loading, setLoading] = useState(true);
  const [creatingChannel, setCreatingChannel] = useState(false);
  const [newChannelType, setNewChannelType] = useState<ChannelType | null>(null);
  const [savingChannelId, setSavingChannelId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successChannelId, setSuccessChannelId] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    setSuccessChannelId(null);

    listChannels(botId)
      .then((items) => {
        if (!isMounted) return;
        setChannels(items);
        const nextForms = Object.fromEntries(
          items.map((channel) => [channel.id, { config: buildConfigState(channel), is_active: channel.is_active }]),
        );
        setForms(nextForms);
        const existingTypes = new Set(items.map((channel) => channel.channel_type));
        const firstAvailable = Object.values(ChannelType).find((type) => !existingTypes.has(type)) ?? null;
        setNewChannelType((prev) => prev ?? firstAvailable);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        const message = err instanceof Error ? err.message : "Не удалось загрузить каналы";
        setError(message);
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

  const handleActiveToggle = (channelId: number, isActive: boolean) => {
    setForms((prev) => ({
      ...prev,
      [channelId]: { ...prev[channelId], is_active: isActive },
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>, channelId: number) => {
    event.preventDefault();
    const form = forms[channelId];
    if (!form) {
      return;
    }

    setSavingChannelId(channelId);
    setError(null);
    setSuccessChannelId(null);

    try {
      const payload = {
        is_active: form.is_active,
        config: prepareConfig(form.config),
      };
      const updatedChannel = await updateChannel(botId, channelId, payload);
      setChannels((prev) => prev.map((item) => (item.id === channelId ? updatedChannel : item)));
      setForms((prev) => ({
        ...prev,
        [channelId]: {
          config: buildConfigState(updatedChannel),
          is_active: updatedChannel.is_active,
        },
      }));
      setSuccessChannelId(channelId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось обновить канал";
      setError(message);
    } finally {
      setSavingChannelId(null);
    }
  };

  const availableChannelTypes = useMemo(() => {
    const existingTypes = new Set(channels.map((channel) => channel.channel_type));
    return Object.values(ChannelType).filter((type) => !existingTypes.has(type));
  }, [channels]);

  const handleAddChannel = async () => {
    if (!newChannelType) {
      return;
    }

    setCreatingChannel(true);
    setError(null);
    setSuccessChannelId(null);

    try {
      const payload = {
        channel_type: newChannelType,
        config: {},
        is_active: false,
      };
      const createdChannel = await createChannel(botId, payload);
      setChannels((prev) => [...prev, createdChannel]);
      setForms((prev) => ({
        ...prev,
        [createdChannel.id]: {
          config: buildConfigState(createdChannel),
          is_active: createdChannel.is_active,
        },
      }));

      const nextAvailable = availableChannelTypes.find((type) => type !== newChannelType) ?? null;
      setNewChannelType(nextAvailable);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось создать канал";
      setError(message);
    } finally {
      setCreatingChannel(false);
    }
  };

  useEffect(() => {
    if (availableChannelTypes.length === 0) {
      setNewChannelType(null);
      return;
    }

    setNewChannelType((prev) => {
      if (prev && availableChannelTypes.includes(prev)) {
        return prev;
      }
      return availableChannelTypes[0] ?? null;
    });
  }, [availableChannelTypes]);

  const renderFields = (channel: BotChannel) => {
    const form = forms[channel.id];
    if (!form) return null;

    const definedFields = CHANNEL_FIELDS[channel.channel_type] ?? [];
    const existingKeys = new Set(definedFields.map((field) => field.key));
    const additionalKeys = Object.keys(form.config).filter((key) => !existingKeys.has(key));

    return (
      <div className={styles.fieldsGrid}>
        {definedFields.map((field) => (
          <label key={field.key} className={styles.field}>
            <span className={styles.fieldLabel}>{field.label}</span>
            {field.type === "textarea" ? (
              <textarea
                className={styles.textarea}
                value={form.config[field.key] ?? ""}
                onChange={(event) => handleConfigChange(channel.id, field.key, event.target.value)}
                placeholder={field.placeholder}
                rows={3}
              />
            ) : (
              <input
                className={styles.input}
                type="text"
                value={form.config[field.key] ?? ""}
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
              value={form.config[key] ?? ""}
              onChange={(event) => handleConfigChange(channel.id, key, event.target.value)}
            />
          </label>
        ))}
      </div>
    );
  };

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
      {!loading && error && <p className={styles.error}>{error}</p>}
      {!loading && !error && channels.length === 0 && (
        <p className={styles.muted}>У бота нет настроенных каналов. Добавьте первый канал.</p>
      )}

      {!loading && !error && availableChannelTypes.length > 0 && (
        <div className={styles.addChannelCard}>
          <div>
            <h4 className={styles.addChannelTitle}>Добавить канал</h4>
            <p className={styles.subtitle}>Выберите тип и создайте новый канал.</p>
          </div>
          <div className={styles.addChannelControls}>
            <label className={styles.fieldLabel} htmlFor="channel-type-select">
              Тип канала
            </label>
            <div className={styles.addChannelRow}>
              <select
                id="channel-type-select"
                className={styles.select}
                value={newChannelType ?? ""}
                onChange={(event) => setNewChannelType(event.target.value as ChannelType)}
              >
                <option value="" disabled>
                  Выберите тип
                </option>
                {availableChannelTypes.map((type) => (
                  <option key={type} value={type}>
                    {CHANNEL_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={styles.saveButton}
                onClick={handleAddChannel}
                disabled={!newChannelType || creatingChannel}
              >
                {creatingChannel ? "Добавляем..." : "Добавить канал"}
              </button>
            </div>
          </div>
        </div>
      )}

      {!loading && !error && channels.map((channel) => {
        const form = forms[channel.id];
        return (
          <form
            key={channel.id}
            className={styles.card}
            onSubmit={(event) => handleSubmit(event, channel.id)}
          >
            <div className={styles.cardHeader}>
              <div>
                <div className={styles.badge}>{CHANNEL_TYPE_LABELS[channel.channel_type]}</div>
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

            {renderFields(channel)}

            <div className={styles.actions}>
              {successChannelId === channel.id && (
                <span className={styles.success}>Настройки сохранены</span>
              )}
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
