"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import LayoutShell from "@/app/components/layout/LayoutShell";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import { DialogStatus } from "@/app/api/types";
import { useDialogsStore } from "@/store/dialogs.store";

import styles from "./page.module.css";

interface DialogDetailsPageProps {
  params: { botId: string; dialogId: string };
}

const STATUS_LABELS: Record<DialogStatus, string> = {
  [DialogStatus.AUTO]: "Автоматический режим",
  [DialogStatus.WAIT_OPERATOR]: "Ожидает оператора",
  [DialogStatus.WAIT_USER]: "Ожидает пользователя",
};

export default function DialogDetailsPage({ params }: DialogDetailsPageProps) {
  const botId = useMemo(() => Number(params.botId), [params.botId]);
  const dialogId = useMemo(() => Number(params.dialogId), [params.dialogId]);
  const invalidIds = Number.isNaN(botId) || Number.isNaN(dialogId);

  const [messageText, setMessageText] = useState("");

  const {
    dialogDetails,
    loadingDialog,
    sendingMessage,
    updatingDialog,
    error,
    fetchDialog,
    sendMessage,
    lockDialog,
    unlockDialog,
    closeDialog,
  } = useDialogsStore();

  const dialog = dialogDetails[dialogId];

  useEffect(() => {
    if (!invalidIds) {
      void fetchDialog(botId, dialogId);
    }
  }, [botId, dialogId, fetchDialog, invalidIds]);

  const handleSend = async () => {
    if (!messageText.trim()) {
      return;
    }
    await sendMessage(botId, dialogId, { text: messageText });
    setMessageText("");
  };

  const handleLockToggle = async () => {
    if (!dialog) {
      return;
    }
    if (dialog.is_locked) {
      await unlockDialog(botId, dialogId);
    } else {
      await lockDialog(botId, dialogId);
    }
  };

  const handleClose = async () => {
    await closeDialog(botId, dialogId);
  };

  return (
    <AuthGuard>
      <LayoutShell title="Диалог" description="Просматривайте сообщения и управляйте статусом диалога.">
        <div className={styles.container}>
          <Link className={styles.backLink} href={`/bots/${botId}/dialogs`}>
            ← Назад к диалогам
          </Link>

          {invalidIds && <p className={styles.error}>Некорректные параметры адреса.</p>}
          {!invalidIds && error && <p className={styles.error}>{error}</p>}
          {!invalidIds && loadingDialog && <p className={styles.muted}>Загружаем диалог...</p>}

          {!invalidIds && !loadingDialog && !dialog && !error && (
            <p className={styles.muted}>Диалог не найден.</p>
          )}

          {dialog && (
            <div className={styles.layout}>
              <div className={styles.infoBox}>
                <div className={styles.infoRow}>
                  <span className={styles.label}>Статус:</span>
                  <span className={styles.status}>{STATUS_LABELS[dialog.status]}</span>
                </div>
                <div className={styles.infoRow}>
                  <span className={styles.label}>Заблокирован:</span>
                  <span className={styles.value}>{dialog.is_locked ? "Да" : "Нет"}</span>
                </div>
                <div className={styles.infoRow}>
                  <span className={styles.label}>Закрыт:</span>
                  <span className={styles.value}>{dialog.closed ? "Да" : "Нет"}</span>
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.button}
                    type="button"
                    onClick={handleLockToggle}
                    disabled={updatingDialog}
                  >
                    {dialog.is_locked ? "Разблокировать" : "Заблокировать"}
                  </button>
                  <button
                    className={styles.button}
                    type="button"
                    onClick={handleClose}
                    disabled={dialog.closed || updatingDialog}
                  >
                    Закрыть диалог
                  </button>
                </div>
              </div>

              <div className={styles.messagesBox}>
                <h3 className={styles.sectionTitle}>Сообщения</h3>
                <div className={styles.messagesList}>
                  {dialog.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`${styles.message} ${styles[message.sender]}`}
                    >
                      <div className={styles.messageHeader}>
                        <span className={styles.sender}>{message.sender}</span>
                        <span className={styles.timestamp}>
                          {new Date(message.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className={styles.text}>
                        {message.text ??
                          (message.payload ? JSON.stringify(message.payload) : "(пустое сообщение)")}
                      </p>
                    </div>
                  ))}
                  {dialog.messages.length === 0 && (
                    <p className={styles.muted}>Сообщения пока отсутствуют.</p>
                  )}
                </div>

                <div className={styles.inputRow}>
                  <textarea
                    value={messageText}
                    onChange={(event) => setMessageText(event.target.value)}
                    placeholder="Введите сообщение оператора..."
                    rows={3}
                  />
                  <button
                    className={styles.button}
                    type="button"
                    onClick={handleSend}
                    disabled={sendingMessage || dialog.closed}
                  >
                    Отправить
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
