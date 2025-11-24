"use client";

import { useMemo } from "react";

import { Bot, DialogStatus } from "@/app/api/types";

import styles from "./SearchFilters.module.css";

interface FilterValues {
  query: string;
  status: DialogStatus | "";
  operatorId: string;
}

interface SearchFiltersProps {
  bots: Bot[];
  selectedBotId: number | null;
  loadingBots: boolean;
  filters: FilterValues;
  onFiltersChange: (values: Partial<FilterValues>) => void;
  onBotChange: (botId: number) => void;
  onSubmit: () => void;
}

const STATUS_LABELS: Record<DialogStatus, string> = {
  [DialogStatus.AUTO]: "Автоматический",
  [DialogStatus.WAIT_OPERATOR]: "Ожидает оператора",
  [DialogStatus.WAIT_USER]: "Ожидает пользователя",
};

export function SearchFilters({
  bots,
  selectedBotId,
  loadingBots,
  filters,
  onFiltersChange,
  onBotChange,
  onSubmit,
}: SearchFiltersProps) {
  const statusOptions = useMemo(() => Object.values(DialogStatus), []);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="bot">
          Бот
        </label>
        <select
          id="bot"
          className={styles.select}
          value={selectedBotId ?? ""}
          onChange={(event) => onBotChange(Number(event.target.value))}
          disabled={loadingBots || bots.length === 0}
        >
          <option value="" disabled>
            {loadingBots ? "Загружаем..." : "Выберите бота"}
          </option>
          {bots.map((bot) => (
            <option key={bot.id} value={bot.id}>
              {bot.name}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="query">
          Запрос
        </label>
        <input
          id="query"
          type="text"
          className={styles.input}
          placeholder="Поиск по сообщениям"
          value={filters.query}
          onChange={(event) => onFiltersChange({ query: event.target.value })}
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="status">
          Статус диалога
        </label>
        <select
          id="status"
          className={styles.select}
          value={filters.status}
          onChange={(event) =>
            onFiltersChange({ status: event.target.value as DialogStatus | "" })
          }
        >
          <option value="">Все статусы</option>
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="operator">
          ID оператора
        </label>
        <input
          id="operator"
          type="number"
          className={styles.input}
          placeholder="Например, 42"
          value={filters.operatorId}
          onChange={(event) => onFiltersChange({ operatorId: event.target.value })}
          min={0}
        />
      </div>

      <div className={styles.buttonRow}>
        <button type="submit" className={styles.button} disabled={!selectedBotId}>
          Найти диалоги
        </button>
      </div>
    </form>
  );
}
