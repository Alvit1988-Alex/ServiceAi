"use client";

import { FormEvent, useEffect, useState } from "react";

import { addBotAdmin, listBotAdmins, removeBotAdmin, updateBot } from "@/app/api/botsApi";
import { BotAdmin } from "@/app/api/types";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { useBotsStore } from "@/store/bots.store";

import styles from "./settings.module.css";

export default function SettingsPage() {
  const { selectedBot, reloadSelectedBot } = useBotsStore();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [admins, setAdmins] = useState<BotAdmin[]>([]);
  const [accountPublicId, setAccountPublicId] = useState("");
  const [role, setRole] = useState<"superadmin" | "admin">("admin");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    setName(selectedBot?.name ?? "");
    setDescription(selectedBot?.description ?? "");
    void loadAdmins();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBot?.id]);

  async function loadAdmins() {
    if (!selectedBot?.id) return;
    try {
      const data = await listBotAdmins(selectedBot.id);
      setAdmins(data);
    } catch {
      setAdmins([]);
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedBot?.id) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await updateBot(selectedBot.id, { name: name.trim(), description: description.trim() || null });
      await reloadSelectedBot();
      setSuccess("Настройки бота сохранены");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setLoading(false);
    }
  }

  async function handleAddAdmin() {
    if (!selectedBot?.id) return;
    setLoading(true);
    setError(null);
    try {
      await addBotAdmin(selectedBot.id, accountPublicId.trim(), role);
      setAccountPublicId("");
      setRole("admin");
      setShowAdd(false);
      await loadAdmins();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка добавления администратора");
    } finally {
      setLoading(false);
    }
  }

  async function handleRemoveAdmin(userId: number) {
    if (!selectedBot?.id) return;
    setLoading(true);
    setError(null);
    try {
      await removeBotAdmin(selectedBot.id, userId);
      await loadAdmins();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка удаления администратора");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard>
      <LayoutShell title="Настройки бота" description="Управление выбранным ботом.">
        {!selectedBot ? (
          <p className={styles.muted}>Выберите бота на странице «Боты», чтобы открыть настройки.</p>
        ) : (
          <div className={styles.page}>
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Название бота</h2>
              <form className={styles.form} onSubmit={handleSave}>
                <input className={styles.input} value={name} onChange={(e) => setName(e.target.value)} required />
                <h2 className={styles.sectionTitle}>Описание</h2>
                <input className={styles.input} value={description} onChange={(e) => setDescription(e.target.value)} />
                <button className={styles.button} type="submit" disabled={loading}>Сохранить</button>
              </form>
            </section>

            <section className={styles.section}>
              <div className={styles.adminHeader}>
                <h2 className={styles.sectionTitle}>Администраторы</h2>
                <button
                  type="button"
                  title="Добавить нового администратора"
                  className={styles.plusBtn}
                  onClick={() => setShowAdd((v) => !v)}
                >
                  +
                </button>
              </div>

              {showAdd && (
                <div className={styles.addRow}>
                  <input
                    className={styles.input}
                    placeholder="ID аккаунта (8 цифр)"
                    value={accountPublicId}
                    onChange={(e) => setAccountPublicId(e.target.value.replace(/\D/g, "").slice(0, 8))}
                  />
                  <select className={styles.input} value={role} onChange={(e) => setRole(e.target.value as "superadmin" | "admin")}>
                    <option value="admin">admin</option>
                    <option value="superadmin">superadmin</option>
                  </select>
                  <button className={styles.button} type="button" onClick={handleAddAdmin} disabled={accountPublicId.length !== 8 || loading}>
                    Добавить
                  </button>
                </div>
              )}

              <div className={styles.form}>
                {admins.map((admin) => (
                  <div key={admin.id} className={styles.adminRow}>
                    <span>
                      {admin.first_name ?? "Пользователь"}
                      {admin.last_name ? ` ${admin.last_name}` : ""} — ID {admin.account_public_id}
                    </span>
                    <button type="button" className={styles.button} onClick={() => handleRemoveAdmin(admin.user_id)}>
                      Удалить
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {error && <p className={styles.error}>{error}</p>}
            {success && <p className={styles.success}>{success}</p>}
          </div>
        )}
      </LayoutShell>
    </AuthGuard>
  );
}
