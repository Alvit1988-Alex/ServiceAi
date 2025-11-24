"use client";

import { useMemo } from "react";

import { ChannelType, DialogShort, DialogStatus } from "@/app/api/types";

import styles from "./SearchResults.module.css";

interface SearchResultsProps {
  items: DialogShort[];
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  perPage: number;
  hasNext: boolean;
  onRowClick: (dialog: DialogShort) => void;
  onPageChange: (page: number) => void;
  onPerPageChange: (perPage: number) => void;
}

const STATUS_LABELS: Record<DialogStatus, string> = {
  [DialogStatus.AUTO]: "Автоматический",
  [DialogStatus.WAIT_OPERATOR]: "Ожидает оператора",
  [DialogStatus.WAIT_USER]: "Ожидает пользователя",
};

const CHANNEL_LABELS: Record<ChannelType, string> = {
  [ChannelType.TELEGRAM]: "Telegram",
  [ChannelType.WHATSAPP_GREEN]: "WhatsApp Business (Green)",
  [ChannelType.WHATSAPP_360]: "WhatsApp 360dialog",  
  [ChannelType.WHATSAPP_CUSTOM]: "WhatsApp кастом",
  [ChannelType.AVITO]: "Avito",
  [ChannelType.MAX]: "Max",
  [ChannelType.WEBCHAT]: "Webchat",
};

function formatDate(date: string | null | undefined): string {
  if (!date) return "—";
  const parsed = new Date(date);
  return parsed.toLocaleString();
}

export function SearchResults({
  items,
  loading,
  error,
  total,
  page,
  perPage,
  hasNext,
  onRowClick,
  onPageChange,
  onPerPageChange,
}: SearchResultsProps) {
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / perPage || 1)), [total, perPage]);

  const handlePrev = () => {
    onPageChange(Math.max(1, page - 1));
  };

  const handleNext = () => {
    onPageChange(Math.min(totalPages, page + 1));
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID диалога</th>
              <th>Канал</th>
              <th>Статус</th>
              <th>Чат</th>
              <th>Оператор</th>
              <th>Последнее сообщение</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className={styles.loading} colSpan={6}>
                  Загружаем результаты...
                </td>
              </tr>
            )}

            {!loading && error && (
              <tr>
                <td className={styles.error} colSpan={6}>
                  {error}
                </td>
              </tr>
            )}

            {!loading && !error && items.length === 0 && (
              <tr>
                <td className={styles.empty} colSpan={6}>
                  Ничего не найдено. Попробуйте изменить запрос.
                </td>
              </tr>
            )}

            {!loading && !error &&
              items.map((dialog) => (
                <tr key={dialog.id} className={styles.row} onClick={() => onRowClick(dialog)}>
                  <td>#{dialog.id}</td>
                  <td>{CHANNEL_LABELS[dialog.channel_type]}</td>
                  <td>{STATUS_LABELS[dialog.status]}</td>
                  <td>{dialog.external_chat_id}</td>
                  <td>{dialog.assigned_admin_id ?? "—"}</td>
                  <td>{formatDate(dialog.last_message_at)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className={styles.pagination}>
        <div className={styles.paginationControls}>
          <button className={styles.button} onClick={handlePrev} disabled={page <= 1 || loading}>
            Назад
          </button>
          <span className={styles.meta}>
            Страница {page} из {totalPages}
          </span>
          <button
            className={styles.button}
            onClick={handleNext}
            disabled={loading || page >= totalPages || !hasNext}
          >
            Вперед
          </button>
        </div>

        <div className={styles.paginationControls}>
          <span className={styles.meta}>Показать на странице:</span>
          <select
            className={styles.perPageSelect}
            value={perPage}
            onChange={(event) => onPerPageChange(Number(event.target.value))}
            disabled={loading}
          >
            {[10, 20, 50].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
