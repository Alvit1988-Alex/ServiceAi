"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "../components/Button/Button";
import LayoutShell from "../components/layout/LayoutShell";
import styles from "../page.module.css";
import { useAuthStore } from "@/store/auth.store";
import QRCode from "qrcode";

function buildTelegramLinks(deeplink: string | null) {
  if (!deeplink) {
    return { webLink: null, tgLink: null };
  }

  try {
    const url = new URL(deeplink);
    const botUsername = url.pathname.replace("/", "");
    const startParam = url.searchParams.get("start");

    if (!botUsername || !startParam) {
      return { webLink: deeplink, tgLink: null };
    }

    return {
      webLink: deeplink,
      tgLink: `tg://resolve?domain=${botUsername}&start=${startParam}`,
    };
  } catch {
    return { webLink: deeplink, tgLink: null };
  }
}

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
  const [copySuccess, setCopySuccess] = useState(false);
  const [showQr, setShowQr] = useState(false);

  const { webLink, tgLink } = useMemo(
    () => buildTelegramLinks(pendingDeeplink),
    [pendingDeeplink],
  );
  const qrLink = tgLink ?? webLink;

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
      if (!qrLink) {
        setQrImage(null);
        return;
      }
      try {
        const url = await QRCode.toDataURL(qrLink);
        setQrImage(url);
      } catch {
        setQrImage(null);
      }
    };
    void generateQr();
  }, [qrLink]);

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
            Используйте Telegram для подтверждения входа. QR-код и ссылка обновляются
            автоматически, если истечет время.
          </p>
        </div>

        <div className={styles.loginForm}>
          <div className={`${styles.actions} ${styles.loginActions}`}>
            <Button
              type="button"
              onClick={async () => {
                setShowQr(false);
                if (tgLink) {
                  window.location.href = tgLink;
                  return;
                }
                if (webLink) {
                  window.open(webLink, "_blank", "noopener,noreferrer");
                  return;
                }
                const deeplink = await ensurePendingLogin();
                if (!deeplink) {
                  return;
                }
                const { tgLink: resolvedTgLink, webLink: resolvedWebLink } =
                  buildTelegramLinks(deeplink);
                if (resolvedTgLink) {
                  window.location.href = resolvedTgLink;
                  return;
                }
                if (resolvedWebLink) {
                  window.open(resolvedWebLink, "_blank", "noopener,noreferrer");
                }
              }}
              disabled={loading || polling}
            >
              {loading || polling ? "Готовим ссылку..." : "Открыть в Telegram"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={async () => {
                if (webLink) {
                  window.open(webLink, "_blank", "noopener,noreferrer");
                  return;
                }
                const deeplink = await ensurePendingLogin();
                if (!deeplink) {
                  return;
                }
                const { webLink: resolvedWebLink } = buildTelegramLinks(deeplink);
                if (resolvedWebLink) {
                  window.open(resolvedWebLink, "_blank", "noopener,noreferrer");
                }
              }}
              disabled={loading || polling}
            >
              {loading || polling ? "Готовим ссылку..." : "Открыть в браузере"}
            </Button>
            <Button
              type="button"
              onClick={async () => {
                setShowQr(true);
                if (!isPendingValid) {
                  await ensurePendingLogin();
                }
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
              <div className={styles.fieldGroup}>
                <p className={styles.fieldLabel}>Как войти</p>
                <ol className={styles.loginDescription}>
                  <li>Откройте Telegram на телефоне.</li>
                  <li>Отсканируйте QR (или нажмите «Открыть в Telegram»).</li>
                  <li>В чате с ботом нажмите Start.</li>
                  <li>Вернитесь в браузер — вход завершится автоматически.</li>
                </ol>
              </div>
              {tgLink && (
                <p className={styles.loginDescription}>
                  <a href={tgLink} target="_blank" rel="noreferrer">
                    Открыть в Telegram
                  </a>
                </p>
              )}
              {webLink && (
                <p className={styles.loginDescription}>
                  <a href={webLink} target="_blank" rel="noreferrer">
                    Если не открылось — откройте в браузере
                  </a>
                </p>
              )}
              <div className={`${styles.actions} ${styles.loginActions}`}>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={async () => {
                    if (!webLink) {
                      return;
                    }
                    try {
                      await navigator.clipboard.writeText(webLink);
                      setCopySuccess(true);
                      window.setTimeout(() => setCopySuccess(false), 2000);
                    } catch {
                      setLocalError("Не удалось скопировать ссылку");
                    }
                  }}
                  disabled={!webLink}
                >
                  {copySuccess ? "Ссылка скопирована" : "Скопировать ссылку"}
                </Button>
              </div>
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
