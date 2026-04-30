"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { startYandexLogin } from "../api/authApi";
import { Button } from "../components/Button/Button";
import LayoutShell from "../components/layout/LayoutShell";
import styles from "./login.module.css";
import { useAuthStore } from "@/store/auth.store";

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  access_denied: "Вход через Яндекс был отменен.",
};

function resolveOauthErrorMessage(message: string | null): string | null {
  if (!message) return null;
  return OAUTH_ERROR_MESSAGES[message] ?? message;
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    completeYandexLogin,
    completeProfile,
    loading,
    error,
    isAuthenticated,
    isInitialized,
    initFromStorage,
    profileCompletionRequired,
  } = useAuthStore();

  const [localError, setLocalError] = useState<string | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const processedTokenRef = useRef<string | null>(null);
  const oauthToken = searchParams.get("oauth_token");
  const oauthError = searchParams.get("oauth_error");

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (isAuthenticated && !profileCompletionRequired) {
      router.replace("/bots");
    }
  }, [isAuthenticated, profileCompletionRequired, router]);

  useEffect(() => {
    if (!oauthError) return;
    setLocalError(resolveOauthErrorMessage(oauthError) ?? "Не удалось выполнить вход через Яндекс.");
    router.replace("/login");
  }, [oauthError, router]);

  useEffect(() => {
    if (!isInitialized || !oauthToken || processedTokenRef.current === oauthToken) return;

    processedTokenRef.current = oauthToken;
    setLocalError(null);

    void (async () => {
      try {
        await completeYandexLogin(oauthToken);
        if (useAuthStore.getState().profileCompletionRequired === true) {
          router.replace("/login");
        } else {
          router.replace("/bots");
        }
      } catch (err) {
        setLocalError(resolveOauthErrorMessage(err instanceof Error ? err.message : null) ?? "Не удалось завершить вход через Яндекс.");
        router.replace("/login");
      }
    })();
  }, [completeYandexLogin, isInitialized, oauthToken, router]);

  const buttonLabel = useMemo(() => {
    if (loading && oauthToken) return "Завершаем вход...";
    if (loading) return "Переходим в Яндекс...";
    return "Войти через Яндекс";
  }, [loading, oauthToken]);

  const handleCompleteProfile = useCallback(() => {
    if (!firstName.trim()) {
      setLocalError("Введите имя *");
      return;
    }
    void completeProfile(firstName.trim(), lastName.trim());
  }, [completeProfile, firstName, lastName]);

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

          {profileCompletionRequired && (
            <div className={styles.profileCompletion}>
              <input className={styles.input} placeholder="Введите имя *" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
              <input className={styles.input} placeholder="Введите фамилию (необязательно)" value={lastName} onChange={(e) => setLastName(e.target.value)} />
              <Button type="button" className={styles.btn} onClick={handleCompleteProfile} disabled={!firstName.trim()}>
                Сохранить профиль
              </Button>
            </div>
          )}

          {(localError || error) && <p className={styles.error}>{localError || error}</p>}
        </div>
      </div>
    </LayoutShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div />}>
      <LoginPageContent />
    </Suspense>
  );
}
