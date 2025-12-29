"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { KnowledgeFile } from "@/app/api/types";
import { useAiStore } from "@/store/ai.store";

import styles from "./BotKnowledge.module.css";

interface BotKnowledgeProps {
  botId: number;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFileSize(size: number): string {
  if (!Number.isFinite(size) || size < 0) {
    return "—";
  }

  const units = ["Б", "КБ", "МБ", "ГБ"];
  let value = size;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function getPaginationFallback(items: KnowledgeFile[]) {
  const total = items.length;
  const perPage = Math.max(1, total || 10);
  return { page: 1, per_page: perPage, total, has_next: false };
}

export default function BotKnowledge({ botId }: BotKnowledgeProps) {
  const {
    knowledgeByBot,
    knowledgePaginationByBot,
    loadingKnowledge,
    uploadingKnowledge,
    deletingKnowledge,
    error,
    loadKnowledge,
    uploadKnowledgeItem,
    deleteKnowledgeItem,
    changeKnowledgePage,
  } = useAiStore();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    loadKnowledge(botId);
  }, [botId, loadKnowledge]);

  const knowledgeItems = useMemo(() => knowledgeByBot[botId] ?? [], [knowledgeByBot, botId]);
  const pagination = knowledgePaginationByBot[botId] ?? getPaginationFallback(knowledgeItems);
  const totalPages = Math.max(1, Math.ceil((pagination.total || knowledgeItems.length) / pagination.per_page));

  const itemsToRender = useMemo(() => {
    const start = (pagination.page - 1) * pagination.per_page;
    return knowledgeItems.slice(start, start + pagination.per_page);
  }, [knowledgeItems, pagination.page, pagination.per_page]);

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatusMessage("");

    if (!selectedFile) {
      setStatusMessage("Выберите файл для загрузки");
      return;
    }

    const uploaded = await uploadKnowledgeItem(botId, selectedFile);
    if (uploaded) {
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setStatusMessage("Файл загружен");
    }
  };

  const handleDelete = async (fileId: number) => {
    setStatusMessage("");
    await deleteKnowledgeItem(botId, fileId);
  };

  const handlePreviousPage = () => changeKnowledgePage(botId, pagination.page - 1);
  const handleNextPage = () => changeKnowledgePage(botId, pagination.page + 1);

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>База знаний</h2>
          <p className={styles.subtitle}>
            Загружайте файлы, чтобы обогатить ответы бота и предоставлять более точную информацию.
          </p>
        </div>

        <div className={styles.badges}>
          {loadingKnowledge && <span className={styles.badge}>Загрузка...</span>}
          {uploadingKnowledge && <span className={styles.badge}>Загружаем файл...</span>}
          {deletingKnowledge && <span className={styles.badge}>Удаление...</span>}
        </div>
      </header>

      {error && <p className={styles.error}>{error}</p>}
      {statusMessage && <p className={styles.success}>{statusMessage}</p>}

      <form className={styles.uploadForm} onSubmit={handleUpload}>
        <label className={styles.label}>
          Файл базы знаний
          <input
            ref={fileInputRef}
            type="file"
            name="file"
            className={styles.fileInput}
            disabled={uploadingKnowledge}
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className={styles.actions}>
          <div className={styles.muted}>Поддерживаются текстовые документы, PDF и другие файлы.</div>
          <button type="submit" className={styles.uploadButton} disabled={!selectedFile || uploadingKnowledge}>
            {uploadingKnowledge ? "Загрузка..." : "Загрузить"}
          </button>
        </div>
      </form>

      <div className={styles.listHeader}>
        <h3 className={styles.listTitle}>Файлы базы знаний</h3>
        <span className={styles.muted}>
          {knowledgeItems.length ? `${knowledgeItems.length} файл(ов)` : "Нет загруженных файлов"}
        </span>
      </div>

      {loadingKnowledge ? (
        <div className={styles.loader}>Загружаем список...</div>
      ) : itemsToRender.length ? (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Название</th>
                <th>Создан</th>
                <th>Размер</th>
                <th>Чанки</th>
                <th>Тип</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {itemsToRender.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className={styles.fileName}>{item.original_name ?? item.file_name}</div>
                    <div className={styles.fileMeta}>{item.file_name}</div>
                  </td>
                  <td>{formatDate(item.created_at)}</td>
                  <td>{formatFileSize(item.size_bytes)}</td>
                  <td>{item.chunks_count}</td>
                  <td>{item.mime_type ?? "—"}</td>
                  <td className={styles.actionsCell}>
                    <button
                      type="button"
                      className={styles.deleteButton}
                      onClick={() => handleDelete(item.id)}
                      disabled={deletingKnowledge}
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className={styles.muted}>Файлы базы знаний еще не загружены.</p>
      )}

      {knowledgeItems.length > 0 && (
        <div className={styles.pagination}>
          <button
            type="button"
            className={styles.pageButton}
            onClick={handlePreviousPage}
            disabled={pagination.page <= 1 || loadingKnowledge}
          >
            Предыдущая
          </button>
          <span className={styles.paginationInfo}>
            Страница {pagination.page} из {totalPages}
          </span>
          <button
            type="button"
            className={styles.pageButton}
            onClick={handleNextPage}
            disabled={!pagination.has_next || loadingKnowledge}
          >
            Следующая
          </button>
        </div>
      )}
    </section>
  );
}
