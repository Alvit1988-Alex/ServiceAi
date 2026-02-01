"use client";

import { type FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { Button } from "@/app/components/Button/Button";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { useBotsStore } from "@/store/bots.store";

import styles from "./page.module.css";

const DESCRIPTION =
  "Просматривайте ботов, переходите к их деталям и отслеживайте состояние из единого списка.";

export default function BotsPage() {
  const router = useRouter();
  const { bots, loadingBots, error, fetchBots, createBot } = useBotsStore();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    void fetchBots();
  }, [fetchBots]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;

    await createBot(name.trim(), description.trim() || null);
    setName("");
    setDescription("");
    setIsCreating(false);
  };

  const hasBots = bots.length > 0;

  return (
    <AuthGuard>
      <LayoutShell title="Боты" description={DESCRIPTION}>
        <section className={styles.section}>
          <div className={styles.wrap}>
            <div className={styles.header}>
              <h2 className={styles.title}>Список ботов</h2>
              <p className={styles.description}>
                Выберите бота, чтобы открыть его подробности или обновить настройки.
              </p>
            </div>

            {error && <p className={styles.error}>{error}</p>}
            {!error && loadingBots && (
              <p className={styles.status}>Загружаем список ботов...</p>
            )}
            {!error && !loadingBots && !hasBots && (
              <p className={styles.status}>Пока нет доступных ботов.</p>
            )}

            {!error && hasBots && (
              <div className={styles.list}>
                {bots.map((bot) => (
                  <Button
                    key={bot.id}
                    type="button"
                    className={styles.botBtn}
                    onClick={() => router.push(`/bots/${bot.id}`)}
                  >
                    {bot.name}
                  </Button>
                ))}
              </div>
            )}

            <div className={styles.createArea}>
              <Button
                type="button"
                className={styles.createBtn}
                onClick={() => setIsCreating((v) => !v)}
              >
                Создать нового бота
              </Button>
              {isCreating && (
                <form className={styles.createForm} onSubmit={handleCreate}>
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="Название"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="Описание (не обязательно)"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                  <Button type="submit" disabled={!name.trim() || loadingBots}>
                    Создать бота
                  </Button>
                </form>
              )}
            </div>
          </div>
        </section>
      </LayoutShell>
    </AuthGuard>
  );
}
