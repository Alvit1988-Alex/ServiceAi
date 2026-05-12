"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { listOperatorDialogs } from "@/app/api/dialogsApi";
import { DialogMessage, DialogShort, DialogStatus, MessageSender } from "@/app/api/types";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { useAuthStore } from "@/store/auth.store";
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
  const currentUser = useAuthStore((state) => state.user);

  const [messageText, setMessageText] = useState("");
  const [activeMessageId, setActiveMessageId] = useState<number | null>(null);
  const [highlightedMessageId, setHighlightedMessageId] = useState<number | null>(null);
  const [operatorDialogs, setOperatorDialogs] = useState<DialogShort[] | null>(null);
  const [operatorDialogsForId, setOperatorDialogsForId] = useState<number | null>(null);
  const [operatorDialogsPanelOpen, setOperatorDialogsPanelOpen] = useState(false);
  const [operatorDialogsLoading, setOperatorDialogsLoading] = useState(false);
  const [operatorDialogsError, setOperatorDialogsError] = useState<string | null>(null);
  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({});

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

  const isLockedByAnother = Boolean(dialog && dialog.is_locked && dialog.assigned_admin_id !== currentUser?.id);
  const isLockedByCurrent = Boolean(dialog && dialog.is_locked && dialog.assigned_admin_id === currentUser?.id);
  const interactionDisabled = Boolean(isLockedByAnother || dialog?.closed || updatingDialog || sendingMessage);

  const getOperatorLabel = (message: DialogMessage): string => {
    const firstName = message.operator_admin?.first_name?.trim();
    const lastName = message.operator_admin?.last_name?.trim();

    if (firstName && lastName) {
      return `${firstName} ${lastName}`;
    }
    if (firstName) {
      return firstName;
    }
    if (lastName) {
      return lastName;
    }
    if (message.operator_admin_id !== null) {
      return `ID: ${message.operator_admin_id}`;
    }

    return "ID: неизвестен";
  };

  const getSenderLabel = (message: DialogMessage): string => {
    if (message.sender === MessageSender.OPERATOR) {
      return getOperatorLabel(message);
    }
    return message.sender === MessageSender.USER ? "USER" : "BOT";
  };

  const findSiblingOperatorMessage = (messageId: number, step: -1 | 1) => {
    if (!dialog) {
      return null;
    }

    const currentIndex = dialog.messages.findIndex((item) => item.id === messageId);
    if (currentIndex < 0) {
      return null;
    }

    const target = dialog.messages[currentIndex];
    if (target.operator_admin_id === null) {
      return null;
    }

    for (let idx = currentIndex + step; idx >= 0 && idx < dialog.messages.length; idx += step) {
      const candidate = dialog.messages[idx];
      if (candidate.sender !== MessageSender.OPERATOR) {
        continue;
      }
      if (candidate.operator_admin_id === target.operator_admin_id) {
        return candidate;
      }
    }

    return null;
  };

  const jumpToMessage = (messageId: number) => {
    const element = messageRefs.current[messageId];
    if (!element) {
      return;
    }

    element.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlightedMessageId(messageId);
    window.setTimeout(() => {
      setHighlightedMessageId((value) => (value === messageId ? null : value));
    }, 1800);
  };

  const handleSend = async () => {
    if (!messageText.trim() || interactionDisabled) {
      return;
    }
    await sendMessage(botId, dialogId, { text: messageText });
    setMessageText("");
  };

  const handleLockToggle = async () => {
    if (!dialog || isLockedByAnother) {
      return;
    }
    if (dialog.is_locked) {
      await unlockDialog(botId, dialogId);
    } else {
      await lockDialog(botId, dialogId);
    }
  };

  const handleClose = async () => {
    if (isLockedByAnother) {
      return;
    }
    await closeDialog(botId, dialogId);
  };

  const loadOperatorDialogs = async (operatorId: number | null) => {
    setOperatorDialogsPanelOpen(true);
    setOperatorDialogsForId(operatorId);
    setOperatorDialogsLoading(true);
    setOperatorDialogsError(null);
    setOperatorDialogs(null);

    if (operatorId === null) {
      setOperatorDialogsLoading(false);
      setOperatorDialogsError("ID оператора неизвестен");
      return;
    }

    try {
      const response = await listOperatorDialogs(botId, operatorId);
      setOperatorDialogs(response.items);
    } catch {
      setOperatorDialogsError("Не удалось загрузить диалоги оператора");
    } finally {
      setOperatorDialogsLoading(false);
    }
  };

  return (
    <AuthGuard>
      <LayoutShell title="Диалог" description="Просматривайте сообщения и управляйте статусом диалога.">
        <div className={styles.container}>
          <Link className={styles.backLink} href={`/search?bot_id=${params.botId}`}>
            ← Назад к диалогам
          </Link>

          {invalidIds && <p className={styles.error}>Некорректные параметры адреса.</p>}
          {!invalidIds && error && <p className={styles.error}>{error}</p>}
          {!invalidIds && loadingDialog && <p className={styles.muted}>Загружаем диалог...</p>}
          {!invalidIds && !loadingDialog && !dialog && !error && <p className={styles.muted}>Диалог не найден.</p>}

          {dialog && (
            <div className={styles.layout}>
              <div className={styles.infoBox}>
                {isLockedByAnother && (
                  <div className={styles.lockBanner}>
                    Диалог ведется оператором: {dialog.assigned_admin?.first_name || dialog.assigned_admin?.last_name
                      ? `${dialog.assigned_admin?.first_name ?? ""} ${dialog.assigned_admin?.last_name ?? ""}`.trim()
                      : `ID: ${dialog.assigned_admin_id ?? "неизвестен"}`} · ID: {dialog.assigned_admin_id ?? "неизвестен"}
                  </div>
                )}
                {isLockedByCurrent && <div className={styles.lockNote}>Диалог закреплён за вами.</div>}

                <div className={styles.infoRow}>
                  <span className={styles.label}>Статус:</span>
                  <span className={styles.status}>{STATUS_LABELS[dialog.status]}</span>
                </div>
                <div className={styles.infoRow}>
                  <span className={styles.label}>Закреплён:</span>
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
                    disabled={updatingDialog || isLockedByAnother}
                  >
                    {dialog.is_locked ? "Открепить" : "Закрепить"}
                  </button>
                  <button
                    className={styles.button}
                    type="button"
                    onClick={handleClose}
                    disabled={dialog.closed || updatingDialog || isLockedByAnother}
                  >
                    Закрыть диалог
                  </button>
                </div>
              </div>

              <div className={styles.messagesBox}>
                <h3 className={styles.sectionTitle}>Сообщения</h3>
                <div className={styles.messagesList}>
                  {dialog.messages.map((message) => {
                    const previousMessage = findSiblingOperatorMessage(message.id, -1);
                    const nextMessage = findSiblingOperatorMessage(message.id, 1);

                    return (
                      <div
                        key={message.id}
                        ref={(element) => {
                          messageRefs.current[message.id] = element;
                        }}
                        className={`${styles.message} ${styles[message.sender]} ${
                          highlightedMessageId === message.id ? styles.highlighted : ""
                        }`}
                      >
                        <div className={styles.messageHeader}>
                          {message.sender === MessageSender.OPERATOR ? (
                            <div className={styles.operatorMenuWrap}>
                              <button
                                type="button"
                                className={styles.operatorButton}
                                onClick={() =>
                                  setActiveMessageId((value) => (value === message.id ? null : message.id))
                                }
                              >
                                {getSenderLabel(message)}
                              </button>
                              {activeMessageId === message.id && (
                                <div className={styles.operatorMenu}>
                                  <div className={styles.operatorMenuId}>
                                    ID: {message.operator_admin_id ?? "неизвестен"}
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => void loadOperatorDialogs(message.operator_admin_id)}
                                  >
                                    Диалоги оператора
                                  </button>
                                  <button
                                    type="button"
                                    disabled={!previousMessage}
                                    onClick={() => previousMessage && jumpToMessage(previousMessage.id)}
                                  >
                                    Предыдущее сообщение
                                  </button>
                                  <button
                                    type="button"
                                    disabled={!nextMessage}
                                    onClick={() => nextMessage && jumpToMessage(nextMessage.id)}
                                  >
                                    Следующее сообщение
                                  </button>
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className={styles.sender}>{getSenderLabel(message)}</span>
                          )}
                          <span className={styles.timestamp}>{new Date(message.created_at).toLocaleString()}</span>
                        </div>

                        <p className={styles.text}>
                          {message.text ??
                            (message.payload ? JSON.stringify(message.payload) : "(пустое сообщение)")}
                        </p>
                      </div>
                    );
                  })}

                  {dialog.messages.length === 0 && (
                    <p className={styles.muted}>Сообщения пока отсутствуют.</p>
                  )}
                </div>

                {operatorDialogsPanelOpen && (
                  <div className={styles.operatorDialogs}>
                    <h4>Диалоги оператора{operatorDialogsForId !== null ? ` · ID: ${operatorDialogsForId}` : ""}</h4>
                    {operatorDialogsLoading && <p className={styles.muted}>Загрузка...</p>}
                    {!operatorDialogsLoading && operatorDialogsError && (
                      <p className={styles.error}>{operatorDialogsError}</p>
                    )}
                    {!operatorDialogsLoading && !operatorDialogsError && operatorDialogs && (
                      <ul>
                        {operatorDialogs.map((item) => (
                          <li key={item.id}>
                            <Link href={`/bots/${botId}/dialogs/${item.id}`}>
                              ID {item.id} · {item.status} · {new Date(item.last_message_at).toLocaleString()}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                <div className={styles.inputRow}>
                  <textarea
                    value={messageText}
                    onChange={(event) => setMessageText(event.target.value)}
                    placeholder="Введите сообщение оператора..."
                    rows={3}
                    disabled={interactionDisabled}
                  />
                  <button
                    className={styles.button}
                    type="button"
                    onClick={handleSend}
                    disabled={interactionDisabled}
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
