"use client";

import { useEffect, useMemo, useState } from "react";

import { listBots } from "@/app/api/botsApi";
import {
  BitrixIntegrationStatus,
  disconnectBitrix,
  getBitrixIntegration,
  startBitrixConnect,
  updateBitrixSettings,
} from "@/app/api/integrationsApi";
import { Bot } from "@/app/api/types";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";

import styles from "./integrations.module.css";

export default function IntegrationsPage() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [selectedBotId, setSelectedBotId] = useState<number | null>(null);
  const [portalDomain, setPortalDomain] = useState("");
  const [status, setStatus] = useState<BitrixIntegrationStatus | null>(null);
  const [openlineId, setOpenlineId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [autoCreateLead, setAutoCreateLead] = useState(true);

  const selectedBot = useMemo(
    () => bots.find((bot) => bot.id === selectedBotId) ?? null,
    [bots, selectedBotId],
  );

  useEffect(() => {
    void loadBots();
  }, []);

  useEffect(() => {
    if (selectedBotId) {
      void loadStatus(selectedBotId);
    }
  }, [selectedBotId]);

  async function loadBots() {
    setLoading(true);
    setError(null);
    try {
      const botsData = await listBots();
      setBots(botsData);

      const params = new URLSearchParams(window.location.search);
      const botFromQuery = Number(params.get("bot") ?? "");
      const hasBotFromQuery = Number.isInteger(botFromQuery) && botFromQuery > 0;
      const queryBotExists = hasBotFromQuery && botsData.some((bot) => bot.id === botFromQuery);

      if (queryBotExists) {
        setSelectedBotId(botFromQuery);
      } else if (botsData.length > 0) {
        setSelectedBotId((prev) => prev ?? botsData[0].id);
      }

      if (params.get("success") === "1") {
        setSuccess("Bitrix24 подключен. Укажите Open Line ID и сохраните настройки.");
        const url = new URL(window.location.href);
        url.searchParams.delete("success");
        window.history.replaceState({}, "", url.toString());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить ботов");
    } finally {
      setLoading(false);
    }
  }

  async function loadStatus(botId: number) {
    setLoading(true);
    setError(null);
    try {
      const value = await getBitrixIntegration(botId);
      setStatus(value);
      setOpenlineId(value.openline_id ?? "");
      setAutoCreateLead(value.auto_create_lead_on_first_message);
      if (value.portal_url) {
        setPortalDomain(new URL(value.portal_url).host);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить статус интеграции");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleConnect() {
    if (!selectedBotId) {
      setError("Выберите бота");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await startBitrixConnect(selectedBotId, portalDomain.trim());
      window.location.href = result.auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось подключить Bitrix24");
      setLoading(false);
    }
  }

  async function handleDisconnect() {
    if (!selectedBotId) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const next = await disconnectBitrix(selectedBotId);
      setStatus(next);
      setOpenlineId(next.openline_id ?? "");
      setAutoCreateLead(next.auto_create_lead_on_first_message);
      setSuccess("Интеграция отключена");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отключить интеграцию");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveSettings(autoCreateLead: boolean) {
    if (!selectedBotId) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const next = await updateBitrixSettings(selectedBotId, {
        openline_id: openlineId.trim() || null,
        auto_create_lead_on_first_message: autoCreateLead,
      });
      setStatus(next);
      setOpenlineId(next.openline_id ?? "");
      setAutoCreateLead(next.auto_create_lead_on_first_message);
      setSuccess("Настройки Bitrix24 сохранены");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить настройки");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard>
      <LayoutShell
        title="Интеграции"
        description="Подключите внешние каналы и CRM для работы операторов."
      >
        <div className={styles.page}>
          <section className={styles.card}>
            <h2>Bitrix24</h2>

            <label className={styles.row}>
              <span className={styles.label}>Бот</span>
              <select
                className={styles.select}
                value={selectedBotId ?? ""}
                onChange={(event) => setSelectedBotId(Number(event.target.value))}
                disabled={loading || bots.length === 0}
              >
                {bots.map((bot) => (
                  <option key={bot.id} value={bot.id}>
                    {bot.name}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.row}>
              <span className={styles.label}>Адрес Bitrix24</span>
              <input
                className={styles.input}
                value={portalDomain}
                onChange={(event) => setPortalDomain(event.target.value)}
                placeholder="mycompany.bitrix24.ru"
                disabled={loading}
              />
            </label>

            <div className={styles.actions}>
              <button
                className={styles.button}
                type="button"
                onClick={handleConnect}
                disabled={loading || !selectedBot}
              >
                {loading ? "Загрузка..." : "Подключить"}
              </button>
              {status?.connected && (
                <button
                  className={`${styles.button} ${styles.secondary}`}
                  type="button"
                  onClick={handleDisconnect}
                  disabled={loading}
                >
                  Отключить
                </button>
              )}
            </div>

            <div className={styles.row}>
              <span className={styles.label}>Статус</span>
              <span className={styles.muted}>
                {status?.connected ? "Подключено" : "Не подключено"}
                {status?.portal_url ? ` · ${status.portal_url}` : ""}
                {status?.connected_at
                  ? ` · ${new Date(status.connected_at).toLocaleString()}`
                  : ""}
              </span>
            </div>

            {status?.connected && !status.openline_id && (
              <p className={styles.warning}>
                Укажите Open Line ID, иначе сообщения не будут отправляться в Bitrix.
              </p>
            )}
          </section>

          <section className={styles.card}>
            <h3>Настройки Bitrix</h3>

            <label className={styles.row}>
              <span className={styles.label}>Open Line ID (LINE)</span>
              <input
                className={styles.input}
                value={openlineId}
                onChange={(event) => setOpenlineId(event.target.value)}
                placeholder="ID открытой линии в Bitrix24 (например 1)."
                disabled={loading}
              />
            </label>

            <label className={styles.row}>
              <span className={styles.label}>
                <input
                  type="checkbox"
                  checked={autoCreateLead}
                  onChange={(event) => setAutoCreateLead(event.target.checked)}
                  disabled={loading || !selectedBotId}
                />{" "}
                Создавать лид автоматически при первом сообщении
              </span>
            </label>

            <div className={styles.actions}>
              <button
                className={styles.button}
                type="button"
                onClick={() => void handleSaveSettings(autoCreateLead)}
                disabled={loading || !selectedBotId}
              >
                Сохранить настройки
              </button>
            </div>

            <p className={styles.muted}>
              Если авто-создание лида отключено, лид можно создавать вручную по диалогу.
            </p>
          </section>

          {error && <p className={styles.error}>{error}</p>}
          {success && <p className={styles.success}>{success}</p>}
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
