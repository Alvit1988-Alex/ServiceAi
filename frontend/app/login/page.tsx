"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
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

    if (url.hostname === "telegram.me") {
      url.hostname = "t.me";
    }

    return {
      webLink: url.toString(),
      tgLink: null,
    };
  } catch {
    return { webLink: deeplink, tgLink: null };
  }
}

const hasValidBotStart = (link: string | null) => {
  if (!link) {
    return false;
  }

  try {
    const url = new URL(link);
    const botUsername = url.pathname.replace("/", "");
    const startParam = url.searchParams.get("start");

    return Boolean(botUsername && startParam);
  } catch {
    return false;
  }
};

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

  const [isMobile, setIsMobile] = useState(false);
  const autoEnsureRef = useRef(false);

  const { webLink } = useMemo(
    () => buildTelegramLinks(pendingDeeplink),
    [pendingDeeplink],
  );
  const qrLink = webLink;

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const mq = window.matchMedia("(max-width: 640px)");
    const update = () => setIsMobile(mq.matches);
    update();

    if (mq.addEventListener) {
      mq.addEventListener("change", update);
      return () => mq.removeEventListener("change", update);
    }

    mq.addListener(update);
    return () => mq.removeListener(update);
  }, []);

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

  const ensurePendingLogin = useCallback(async () => {
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
  }, [isPendingValid, pendingDeeplink, startTelegramLogin]);

  useEffect(() => {
    if (!isInitialized || isMobile || loading || polling) {
      if (isMobile) {
        autoEnsureRef.current = false;
      }
      return;
    }

    if (isPendingValid) {
      return;
    }

    if (autoEnsureRef.current) {
      return;
    }

    autoEnsureRef.current = true;
    void ensurePendingLogin().finally(() => {
      autoEnsureRef.current = false;
    });
  }, [ensurePendingLogin, isInitialized, isMobile, isPendingValid, loading, polling]);

  const getTelegramWebLink = useCallback(async () => {
    if (webLink && hasValidBotStart(webLink)) {
      return webLink;
    }

    const deeplink = await ensurePendingLogin();
    if (!deeplink) {
      return null;
    }
    const { webLink: resolvedWebLink } = buildTelegramLinks(deeplink);
    return resolvedWebLink;
  }, [ensurePendingLogin, webLink]);

  const openExternalLink = useCallback(async (getLink: () => Promise<string | null>) => {
    const w = window.open("", "_blank");
    if (w) {
      try {
        w.opener = null;
      } catch {
        // Ignore if the browser blocks access.
      }
    }

    let link: string | null = null;
    try {
      link = await getLink();
    } catch {
      if (w) {
        w.close();
      }
      return;
    }

    if (!link) {
      if (w) {
        w.close();
      }
      return;
    }

    if (w) {
      w.location.replace(link);
      w.focus?.();
    } else {
      window.location.href = link;
    }
  }, []);

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
            Используйте Telegram для подтверждения входа. QR-код и ссылка обновляются автоматически,
            если истечет время.
          </p>
        </div>

        <div className={styles.loginForm}>
          <div className={`${styles.actions} ${styles.loginActions}`}>
            <Button
              type="button"
              onClick={async () => {
                await openExternalLink(getTelegramWebLink);
              }}
              disabled={loading || polling}
            >
              {loading || polling ? "Готовим ссылку..." : "Войти через Telegram"}
            </Button>
          </div>

          {(localError || error) && <p className={styles.errorText}>{localError || error}</p>}

          {pendingDeeplink && (
            <>
              <p className={styles.qrSeparator}>или сканировать QR-код</p>
              <div className={`${styles.fieldGroup} ${styles.qrBlock}`}>
                <p className={styles.fieldLabel}>Отсканируйте QR в Telegram</p>
                {qrImage ? (
                  <Image
                    src={qrImage}
                    alt="QR для входа через Telegram"
                    className={styles.qrImage}
                    width={240}
                    height={240}
                    unoptimized
                  />
                ) : (
                  <p className={styles.errorText}>Не удалось сгенерировать QR. Попробуйте еще раз.</p>
                )}

                <div className={styles.fieldGroup}>
                  <p className={styles.fieldLabel}>Как войти</p>
                  <ol className={styles.loginDescription}>
                    <li>Откройте Telegram на телефоне.</li>
                    <li>Отсканируйте QR (или нажмите «Войти через Telegram»).</li>
                    <li>В чате с ботом нажмите Start.</li>
                    <li>Вернитесь в браузер — вход завершится автоматически.</li>
                  </ol>
                </div>

                {webLink && (
                  <p className={styles.loginDescription}>
                    <a href={webLink} target="_blank" rel="noreferrer">
                      Открыть в браузере
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
                  Статус:{" "}
                  {pendingStatus === "confirmed" ? "Подтверждено" : "Ожидание подтверждения"}
                </p>
              </div>
            </>
          )}

          {!pendingDeeplink && isInitialized && (
            <p className={styles.loginDescription}>
              {isMobile
                ? "Нажмите «Войти через Telegram» для входа."
                : "Нажмите «Войти через Telegram» или сканируйте QR-код ниже."}
            </p>
          )}
        </div>
      </section>
    </LayoutShell>
  );
}
