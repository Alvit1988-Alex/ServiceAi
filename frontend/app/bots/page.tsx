"use client";

import { type FormEvent, useEffect, useState } from "react";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { BotCard } from "@/app/components/bots/BotCard";
import { Button } from "@/app/components/Button/Button";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { useBotsStore } from "@/store/bots.store";

import styles from "./page.module.css";

const DESCRIPTION =
  "Просматривайте ботов, переходите к их деталям и отслеживайте состояние из единого списка.";

export default function BotsPage() {
  const { bots, loadingBots, error, fetchBots, createBot } = useBotsStore();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;

    await createBot(name.trim(), description.trim() || null);
    setName("");
    setDescription("");
  };

  const hasBots = bots.length > 0;

  return (
    <AuthGuard>
      <LayoutShell title="Боты" description={DESCRIPTION}>
        <section className={styles.section}>
          <div className={styles.header}>
            <h2 className={styles.title}>Список ботов</h2>
            <p className={styles.description}>
              Выберите бота, чтобы открыть его подробности или обновить настройки.
            </p>
          </div>

          <form className={styles.createForm} onSubmit={handleCreate}>
            <input
              className={styles.input}
              type="text"
              placeholder="Название бота"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <input
              className={styles.input}
              type="text"
              placeholder="Описание (необязательно)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Button type="submit" disabled={!name.trim() || loadingBots}>
              Создать бота
            </Button>
          </form>

          {error && <p className={styles.error}>{error}</p>}
          {!error && loadingBots && (
            <p className={styles.status}>Загружаем список ботов...</p>
          )}
          {!error && !loadingBots && !hasBots && (
            <p className={styles.status}>Пока нет доступных ботов.</p>
          )}

          {!error && hasBots && (
            <div className={styles.grid}>
              {bots.map((bot) => (
                <BotCard key={bot.id} bot={bot} />
              ))}
            </div>
          )}
        </section>
      </LayoutShell>
    </AuthGuard>
  );
}
