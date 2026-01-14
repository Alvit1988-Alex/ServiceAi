"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { KnowledgeFile } from "@/app/api/types";
import { useAiStore } from "@/store/ai.store";

import DemoAiChat from "./DemoAiChat";
import styles from "./BotAiSetup.module.css";

interface BotAiSetupProps {
  botId: number;
}

const instructionsHintText =
  'Введите сюда инструкции как ИИ-агент должен себя вести, например: "будь вежлив и старайся подробно объяснить информацию" или "ты профессиональный продавец, будь настойчив и аккуратно уговаривай клиента совершить сделку"';

const knowledgeHintText =
  "Добавьте файл с материалами которые бот должен использовать при консультации и на которые он должен опираться давая ответы. Это могут быть особенности работы компании, описание товаров, стоимость услуг, или скрипты по которым работают ваши консультанты.";

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

export default function BotAiSetup({ botId }: BotAiSetupProps) {
  const {
    instructionsByBot,
    loadingInstructions,
    savingInstructions,
    loadingKnowledge,
    uploadingKnowledge,
    deletingKnowledge,
    knowledgeByBot,
    knowledgePaginationByBot,
    error,
    loadInstructions,
    saveInstructions,
    loadKnowledge,
    uploadKnowledgeItem,
    deleteKnowledgeItem,
    changeKnowledgePage,
  } = useAiStore();

  const currentInstructions = instructionsByBot[botId];
  const [systemPrompt, setSystemPrompt] = useState(currentInstructions?.system_prompt ?? "");
  const [successMessage, setSuccessMessage] = useState("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let isMounted = true;
    loadInstructions(botId).then((loaded) => {
      if (!isMounted || !loaded) {
        return;
      }
      setSystemPrompt(loaded.system_prompt ?? "");
    });

    return () => {
      isMounted = false;
    };
  }, [botId, loadInstructions]);

  useEffect(() => {
    if (currentInstructions) {
      setSystemPrompt(currentInstructions.system_prompt ?? "");
    }
  }, [currentInstructions]);

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSuccessMessage("");

    const updated = await saveInstructions(botId, systemPrompt);
    if (updated) {
      setSystemPrompt(updated.system_prompt ?? "");
      setSuccessMessage("Инструкции сохранены");
    }
  };

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
    <div className={styles.layout}>
      <section className={styles.card}>
        <header className={styles.header}>
          <div>
            <div className={styles.titleRow}>
              <h2 className={styles.title}>Инструкции ИИ</h2>
              <span className={styles.hint} title={instructionsHintText}>
                ⓘ
              </span>
            </div>
            <p className={styles.subtitle}>Задайте системные подсказки, которые помогут боту работать точнее.</p>
          </div>

          {loadingInstructions ? (
            <span className={styles.badge}>Загрузка...</span>
          ) : (
            <span className={styles.badge}>Готово</span>
          )}
        </header>

        {error && <p className={styles.error}>{error}</p>}

        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.label}>
            Системные инструкции
            <textarea
              className={styles.textarea}
              value={systemPrompt}
              onChange={(event) => setSystemPrompt(event.target.value)}
              placeholder="Например: Будь вежлив, отвечай на русском языке."
              disabled={loadingInstructions || savingInstructions}
            />
          </label>

          <div className={styles.actions}>
            {successMessage ? (
              <span className={styles.success}>{successMessage}</span>
            ) : (
              <p className={styles.muted}>Не забудьте сохранить изменения</p>
            )}

            <button type="submit" className={styles.saveButton} disabled={savingInstructions}>
              {savingInstructions ? "Сохранение..." : "Сохранить"}
            </button>
          </div>
        </form>
      </section>

      <section className={styles.card}>
        <header className={styles.header}>
          <div>
            <div className={styles.titleRow}>
              <h2 className={styles.title}>Добавить базу знаний</h2>
              <span className={styles.hint} title={knowledgeHintText}>
                ⓘ
              </span>
            </div>
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

      <DemoAiChat botId={botId} />
    </div>
  );
}
