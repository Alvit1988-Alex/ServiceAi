"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAiStore } from "@/store/ai.store";

import styles from "./BotAiInstructions.module.css";

interface BotAiInstructionsProps {
  botId: number;
}

export default function BotAiInstructions({ botId }: BotAiInstructionsProps) {
  const {
    instructionsByBot,
    loadingInstructions,
    savingInstructions,
    error,
    loadInstructions,
    saveInstructions,
  } = useAiStore();

  const currentInstructions = instructionsByBot[botId];
  const [systemPrompt, setSystemPrompt] = useState(currentInstructions?.system_prompt ?? "");
  const [successMessage, setSuccessMessage] = useState("");

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSuccessMessage("");

    const updated = await saveInstructions(botId, systemPrompt);
    if (updated) {
      setSystemPrompt(updated.system_prompt ?? "");
      setSuccessMessage("Инструкции сохранены");
    }
  };

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Инструкции ИИ</h2>
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
          {successMessage ? <span className={styles.success}>{successMessage}</span> : <p className={styles.muted}>Не забудьте сохранить изменения</p>}

          <button type="submit" className={styles.saveButton} disabled={savingInstructions}>
            {savingInstructions ? "Сохранение..." : "Сохранить"}
          </button>
        </div>
      </form>
    </section>
  );
}
