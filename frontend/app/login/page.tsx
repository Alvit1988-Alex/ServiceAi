"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "../components/Button/Button";
import LayoutShell from "../components/layout/LayoutShell";
import styles from "../page.module.css";
import { useAuthStore } from "@/store/auth.store";

export default function LoginPage() {
  const router = useRouter();
  const { login, loading, error } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось войти";
      setLocalError(message);
    }
  };

  return (
    <LayoutShell title="Вход" description="Авторизация в ServiceAI">
      <section className={styles.loginSection}>
        <div className={styles.loginHeader}>
          <h2 className={styles.loginTitle}>Вход в панель управления</h2>
          <p className={styles.loginDescription}>
            Используйте корпоративную почту или логин, чтобы получить доступ к
            аналитике и настройкам сервисов.
          </p>
        </div>

        <form className={styles.loginForm} onSubmit={handleSubmit}>
          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel} htmlFor="email">
              Email
            </label>
            <input
              className={styles.fieldInput}
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              placeholder="name@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className={styles.fieldGroup}>
            <label className={styles.fieldLabel} htmlFor="password">
              Пароль
            </label>
            <input
              className={styles.fieldInput}
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {(localError || error) && (
            <p className={styles.errorText}>{localError || error}</p>
          )}

          <div className={styles.actions}>
            <Button type="submit" disabled={loading}>
              {loading ? "Входим..." : "Войти"}
            </Button>
          </div>
        </form>
      </section>
    </LayoutShell>
  );
}
