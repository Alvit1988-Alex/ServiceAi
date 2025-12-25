"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "../components/Button/Button";
import LayoutShell from "../components/layout/LayoutShell";
import styles from "../page.module.css";
import { useAuthStore } from "@/store/auth.store";
import QRCode from "qrcode";

export default function LoginPage() {
  const router = useRouter();
  const {
    startTelegramLogin,
    pendingDeeplink,
    pendingExpiresAt,
    pendingStatus,
    polling,
    loading,
    error,
    isAuthenticated,
    isInitialized,
    initFromStorage,
    stopTelegramLoginPolling,
  } = useAuthStore();
  const [qrImage, setQrImage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [showQr, setShowQr] = useState(false);

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    const generateQr = async () => {
      if (!pendingDeeplink) {
        setQrImage(null);
        return;
      }
      try {
        const url = await QRCode.toDataURL(pendingDeeplink);
        setQrImage(url);
      } catch {
        setQrImage(null);
      }
    };
    void generateQr();
  }, [pendingDeeplink]);

  useEffect(() => {
    return () => {
      stopTelegramLoginPolling();
    };
  }, [stopTelegramLoginPolling]);

  const isPendingValid =
    pendingDeeplink && pendingExpiresAt && new Date(pendingExpiresAt) > new Date();

  const ensurePendingLogin = async () => {
    setLocalError(null);
    try {
      if (isPendingValid) {
        return pendingDeeplink;
      }
      const pending = await startTelegramLogin();
      return pending.telegram_deeplink;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось подготовить вход";
      setLocalError(message);
      return null;
    }
  };

  const expiresAt = pendingExpiresAt ? new Date(pendingExpiresAt) : null;
  const timeLeft =
    expiresAt && expiresAt > new Date()
      ? Math.max(0, Math.round((expiresAt.getTime() - Date.now()) / 1000))
      : null;

  return (
    <LayoutShell title="Вход" description="Авторизация в ServiceAI">
      <section className={styles.loginSection}>
        <div className={styles.loginHeader}>
          <h2 className={styles.loginTitle}>Вход в панель управления</h2>
          <p className={styles.loginDescription}>
            Откройте Telegram, отсканируйте QR-код и подтвердите вход через
            бота. При истечении времени QR обновится автоматически.
          </p>
        </div>

        <div className={styles.loginForm}>
          <div className={`${styles.actions} ${styles.loginActions}`}>
            <Button
              type="button"
              onClick={async () => {
                setShowQr(false);
                const deeplink = await ensurePendingLogin();
                if (deeplink) {
                  window.open(deeplink, "_blank", "noopener,noreferrer");
                }
              }}
              disabled={loading || polling}
            >
              {loading || polling ? "Готовим ссылку..." : "Войти через Telegram"}
            </Button>
            <Button
              type="button"
              onClick={async () => {
                setShowQr(true);
                await ensurePendingLogin();
              }}
              disabled={loading || polling}
            >
              {loading || polling ? "Готовим QR..." : "Показать QR для входа"}
            </Button>
          </div>

          {(localError || error) && (
            <p className={styles.errorText}>{localError || error}</p>
          )}

          {pendingDeeplink && showQr && (
            <div className={`${styles.fieldGroup} ${styles.qrBlock}`}>
              <p className={styles.fieldLabel}>Отсканируйте QR в Telegram</p>
              {qrImage ? (
                <img
                  src={qrImage}
                  alt="QR для входа через Telegram"
                  className={styles.qrImage}
                />
              ) : (
                <p className={styles.errorText}>Не удалось сгенерировать QR. Попробуйте еще раз.</p>
              )}
              <p className={styles.loginDescription}>
                Или откройте ссылку:{" "}
                <a href={pendingDeeplink} target="_blank" rel="noreferrer">
                  {pendingDeeplink}
                </a>
              </p>
              {timeLeft !== null && (
                <p className={styles.loginDescription}>
                  QR истекает через {timeLeft} сек. После истечения создадим новый автоматически.
                </p>
              )}
              <p className={styles.loginDescription}>
                Статус: {pendingStatus === "confirmed" ? "Подтверждено" : "Ожидание подтверждения"}
              </p>
            </div>
          )}

          {!pendingDeeplink && isInitialized && (
            <p className={styles.loginDescription}>
              Выберите удобный способ входа через Telegram. Мы подготовим ссылку или QR-код для
              подтверждения.
            </p>
          )}
        </div>
      </section>
    </LayoutShell>
  );
}
