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
  const [navigationMessageId, setNavigationMessageId] = useState<number | null>(null);
  const [hasNavigatedToPrevious, setHasNavigatedToPrevious] = useState(false);
  const [operatorDialogs, setOperatorDialogs] = useState<DialogShort[] | null>(null);
  const [operatorDialogsForId, setOperatorDialogsForId] = useState<number | null>(null);
  const [operatorDialogsModalOpen, setOperatorDialogsModalOpen] = useState(false);
  const [operatorDialogsLoading, setOperatorDialogsLoading] = useState(false);
  const [operatorDialogsError, setOperatorDialogsError] = useState<string | null>(null);

  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const activeMenuRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    if (activeMessageId === null) {
      return;
    }

    const handleOutsideClick = (event: MouseEvent) => {
      if (!activeMenuRef.current?.contains(event.target as Node)) {
        setActiveMessageId(null);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [activeMessageId]);

  const isLockedByAnother = Boolean(dialog && dialog.is_locked && dialog.assigned_admin_id !== currentUser?.id);
  const isLockedByCurrent = Boolean(dialog && dialog.is_locked && dialog.assigned_admin_id === currentUser?.id);
  const interactionDisabled = Boolean(isLockedByAnother || dialog?.closed || updatingDialog || sendingMessage);

  const getOperatorLabel = (message: DialogMessage): string => {
    if (message.operator_admin_id === null) {
      return "Оператор (до обновления)";
    }

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

    return `ID: ${message.operator_admin_id}`;
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
    if (target.sender !== MessageSender.OPERATOR || target.operator_admin_id === null) {
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

  const loadOperatorDialogs = async (operatorId: number) => {
    setOperatorDialogsModalOpen(true);
    setOperatorDialogsForId(operatorId);
    setOperatorDialogsLoading(true);
    setOperatorDialogsError(null);
    setOperatorDialogs(null);
    setActiveMessageId(null);

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
                    Диалог ведётся оператором: {dialog.assigned_admin?.first_name || dialog.assigned_admin?.last_name
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
                    Завершить диалог
                  </button>
                </div>
              </div>

              <div className={styles.messagesBox}>
                <h3 className={styles.sectionTitle}>Сообщения</h3>
                <div className={styles.messagesList}>
                  {dialog.messages.map((message) => {
                    const previousMessage = findSiblingOperatorMessage(message.id, -1);
                    const navigationBaseId = navigationMessageId === null ? message.id : navigationMessageId;
                    const nextMessage = hasNavigatedToPrevious ? findSiblingOperatorMessage(navigationBaseId, 1) : null;
                    const isOperatorWithId =
                      message.sender === MessageSender.OPERATOR && message.operator_admin_id !== null;
                    const isLegacyOperator =
                      message.sender === MessageSender.OPERATOR && message.operator_admin_id === null;

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
                          {isOperatorWithId ? (
                            <div
                              className={styles.operatorMenuWrap}
                              ref={activeMessageId === message.id ? activeMenuRef : null}
                            >
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
                                  <div className={styles.operatorMenuId}>ID: {message.operator_admin_id}</div>
                                  <button
                                    type="button"
                                    onClick={() => void loadOperatorDialogs(message.operator_admin_id as number)}
                                  >
                                    Диалоги оператора
                                  </button>
                                  <button
                                    type="button"
                                    disabled={!previousMessage}
                                    onClick={() => {
                                      if (!previousMessage) {
                                        return;
                                      }
                                      jumpToMessage(previousMessage.id);
                                      setNavigationMessageId(previousMessage.id);
                                      setHasNavigatedToPrevious(true);
                                      setActiveMessageId(null);
                                    }}
                                  >
                                    Предыдущее сообщение
                                  </button>
                                  <button
                                    type="button"
                                    disabled={!nextMessage}
                                    onClick={() => {
                                      if (!nextMessage) {
                                        return;
                                      }
                                      jumpToMessage(nextMessage.id);
                                      setNavigationMessageId(nextMessage.id);
                                      setActiveMessageId(null);
                                    }}
                                  >
                                    Следующее сообщение
                                  </button>
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className={styles.sender}>{isLegacyOperator ? "Оператор" : getSenderLabel(message)}</span>
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

                  {dialog.messages.length === 0 && <p className={styles.muted}>Сообщения пока отсутствуют.</p>}
                </div>

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

          {operatorDialogsModalOpen && (
            <div
              className={styles.modalBackdrop}
              onClick={() => {
                setOperatorDialogsModalOpen(false);
              }}
            >
              <div className={styles.modal} onClick={(event) => event.stopPropagation()}>
                <div className={styles.modalHeader}>
                  <h4>Диалоги оператора · ID: {operatorDialogsForId}</h4>
                  <button
                    type="button"
                    className={styles.modalClose}
                    onClick={() => setOperatorDialogsModalOpen(false)}
                  >
                    Закрыть
                  </button>
                </div>

                {operatorDialogsLoading && <p className={styles.muted}>Загрузка...</p>}
                {!operatorDialogsLoading && operatorDialogsError && <p className={styles.error}>{operatorDialogsError}</p>}
                {!operatorDialogsLoading && !operatorDialogsError && operatorDialogs?.length === 0 && (
                  <p className={styles.muted}>Диалоги не найдены</p>
                )}
                {!operatorDialogsLoading && !operatorDialogsError && operatorDialogs && operatorDialogs.length > 0 && (
                  <ul className={styles.operatorDialogsList}>
                    {operatorDialogs.map((item) => (
                      <li key={item.id}>
                        <Link href={`/bots/${botId}/dialogs/${item.id}`}>
                          ID {item.id} · {STATUS_LABELS[item.status]} · {new Date(item.last_message_at).toLocaleString()}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
