"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { startYandexLogin } from "../api/authApi";
import { Button } from "../components/Button/Button";
import LayoutShell from "../components/layout/LayoutShell";
import styles from "./login.module.css";
import { useAuthStore } from "@/store/auth.store";

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  access_denied: "Вход через Яндекс был отменен.",
  account_conflict: "Этот Яндекс-аккаунт уже привязан к другому пользователю.",
  completion_token_consumed: "Ссылка для завершения входа уже использована.",
  completion_token_expired: "Время завершения входа истекло. Попробуйте снова.",
  email_required: "Яндекс не передал email. Используйте аккаунт с подтвержденной почтой.",
  expired_state: "Время ожидания входа истекло. Попробуйте снова.",
  invalid_completion_token: "Не удалось завершить вход. Попробуйте снова.",
  invalid_request: "Не удалось обработать ответ Яндекса. Попробуйте снова.",
  invalid_state: "Не удалось подтвердить запрос входа. Попробуйте снова.",
  oauth_unavailable: "Вход через Яндекс сейчас недоступен.",
  profile_fetch_failed: "Не удалось получить профиль Яндекса. Попробуйте снова.",
  provider_unavailable: "Сервис Яндекса временно недоступен. Попробуйте позже.",
  token_exchange_failed: "Не удалось подтвердить вход через Яндекс. Попробуйте снова.",
  user_unavailable: "Пользователь недоступен для входа.",
};

const OAUTH_DETAIL_MESSAGES: Record<string, string> = {
  "Yandex account email is required": "Яндекс не передал email. Используйте аккаунт с подтвержденной почтой.",
  "Yandex account is already linked to another user": "Этот Яндекс-аккаунт уже привязан к другому пользователю.",
  "Yandex login failed": "Не удалось выполнить вход через Яндекс.",
  "Yandex login session expired": "Время завершения входа истекло. Попробуйте снова.",
  "Yandex OAuth is not configured": "Вход через Яндекс сейчас недоступен.",
  "Yandex OAuth provider error": "Сервис Яндекса временно недоступен. Попробуйте позже.",
  "User is unavailable": "Пользователь недоступен для входа.",
};

function resolveOauthErrorMessage(message: string | null): string | null {
  if (!message) {
    return null;
  }

  return OAUTH_ERROR_MESSAGES[message] ?? OAUTH_DETAIL_MESSAGES[message] ?? message;
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    completeYandexLogin,
    loading,
    error,
    isAuthenticated,
    isInitialized,
    initFromStorage,
  } = useAuthStore();

  const [localError, setLocalError] = useState<string | null>(null);
  const processedTokenRef = useRef<string | null>(null);
  const oauthToken = searchParams.get("oauth_token");
  const oauthError = searchParams.get("oauth_error");

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/bots");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!oauthError) {
      return;
    }

    setLocalError(resolveOauthErrorMessage(oauthError) ?? "Не удалось выполнить вход через Яндекс.");
    router.replace("/login");
  }, [oauthError, router]);

  useEffect(() => {
    if (!isInitialized || !oauthToken || processedTokenRef.current === oauthToken) {
      return;
    }

    processedTokenRef.current = oauthToken;
    setLocalError(null);

    void (async () => {
      try {
        await completeYandexLogin(oauthToken);
        router.replace("/bots");
      } catch (err) {
        setLocalError(resolveOauthErrorMessage(err instanceof Error ? err.message : null) ?? "Не удалось завершить вход через Яндекс.");
        router.replace("/login");
      }
    })();
  }, [completeYandexLogin, isInitialized, oauthToken, router]);

  const buttonLabel = useMemo(() => {
    if (loading && oauthToken) {
      return "Завершаем вход...";
    }
    if (loading) {
      return "Переходим в Яндекс...";
    }
    return "Войти через Яндекс";
  }, [loading, oauthToken]);

  const handleLogin = useCallback(() => {
    setLocalError(null);

    void (async () => {
      try {
        const { auth_url } = await startYandexLogin();
        window.location.href = auth_url;
      } catch (err) {
        setLocalError(resolveOauthErrorMessage(err instanceof Error ? err.message : null) ?? "Не удалось начать вход через Яндекс.");
      }
    })();
  }, []);

  return (
    <LayoutShell title="Вход" description="Авторизация в ServiceAI">
      <div className={styles.screen}>
        <div className={styles.panel}>
          <div className={styles.loginGrid}>
            <div className={styles.buttonCell}>
              <Button type="button" className={styles.btn} onClick={handleLogin} disabled={loading}>
                {buttonLabel}
              </Button>
            </div>
          </div>
          {(localError || error) && <p className={styles.error}>{localError || error}</p>}
        </div>
      </div>
    </LayoutShell>
  );
}
