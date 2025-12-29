"use client";

import Link from "next/link";
import { useEffect, useMemo } from "react";

import LayoutShell from "@/app/components/layout/LayoutShell";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { VISIBLE_CHANNEL_TYPES } from "@/app/api/types";
import { useDialogsStore } from "@/store/dialogs.store";

import styles from "./page.module.css";

interface DialogsPageProps {
  params: { botId: string };
}

const STATUS_LABELS: Record<string, string> = {
  wait_operator: "Ожидает оператора",
  wait_user: "Ожидает пользователя",
  auto: "Автоматический режим",
};

export default function DialogsPage({ params }: DialogsPageProps) {
  const botId = useMemo(() => Number(params.botId), [params.botId]);
  const invalidId = Number.isNaN(botId);

  const { dialogsByBot, loadingList, error, fetchDialogs } = useDialogsStore();
  const dialogs = dialogsByBot[botId] ?? [];
  const visibleDialogs = dialogs.filter((dialog) => VISIBLE_CHANNEL_TYPES.includes(dialog.channel_type));

  useEffect(() => {
    if (!invalidId) {
      void fetchDialogs(botId);
    }
  }, [botId, fetchDialogs, invalidId]);

  return (
    <AuthGuard>
      <LayoutShell title="Диалоги" description="Просматривайте и управляйте активными диалогами бота.">
        <div className={styles.container}>
          <Link className={styles.backLink} href={`/bots/${botId}`}>
            ← Назад к боту
          </Link>

          {invalidId && <p className={styles.error}>Некорректный идентификатор бота.</p>}
          {!invalidId && error && <p className={styles.error}>{error}</p>}
          {!invalidId && loadingList && <p className={styles.muted}>Загружаем диалоги...</p>}

          {!invalidId && !loadingList && visibleDialogs.length === 0 && !error && (
            <p className={styles.muted}>Диалоги пока отсутствуют.</p>
          )}

          <div className={styles.list}>
            {visibleDialogs.map((dialog) => {
              const preview =
                dialog.last_message?.text ??
                (dialog.last_message?.payload ? "Служебное сообщение" : "Нет сообщений");

              return (
                <Link
                  key={dialog.id}
                  className={styles.card}
                  href={`/bots/${dialog.bot_id}/dialogs/${dialog.id}`}
                >
                  <div className={styles.cardHeader}>
                    <div className={styles.statusGroup}>
                      <span className={styles.status}>{STATUS_LABELS[dialog.status] ?? dialog.status}</span>
                      {dialog.closed && <span className={styles.closed}>Закрыт</span>}
                      {dialog.is_locked && <span className={styles.locked}>Заблокирован</span>}
                    </div>
                    <span className={styles.meta}>ID: {dialog.id}</span>
                  </div>

                  <p className={styles.meta}>
                    Канал: {dialog.channel_type} • Чат: {dialog.external_chat_id}
                  </p>
                  <p className={styles.message}>{preview}</p>
                  <div className={styles.metaRow}>
                    <span>Последнее сообщение: {new Date(dialog.last_message_at).toLocaleString()}</span>
                    <span>Непрочитано: {dialog.unread_messages_count}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
