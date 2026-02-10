"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "../components/Button/Button";
import LayoutShell from "../components/layout/LayoutShell";
import styles from "./login.module.css";
import { useAuthStore } from "@/store/auth.store";
import QRCode from "qrcode";

function buildTelegramLinks(deeplink: string | null) {
  if (!deeplink) {
    return { webLink: null };
  }

  try {
    const url = new URL(deeplink);
    const normalizedHost = url.hostname === "telegram.me" ? "t.me" : url.hostname;
    let botUsername = "";
    let startParam: string | null = null;

    if (normalizedHost === "web.telegram.org") {
      const rawHash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;

      if (rawHash.startsWith("?")) {
        const hashParams = new URLSearchParams(rawHash.slice(1));
        const tgaddr = hashParams.get("tgaddr");

        if (tgaddr) {
          try {
            const decoded = decodeURIComponent(tgaddr);
            const tgUrl = new URL(decoded);
            const domain = tgUrl.searchParams.get("domain");
            const start = tgUrl.searchParams.get("start");

            if (domain && start) {
              botUsername = domain;
              startParam = start;
            }
          } catch {
            // Ничего не делать.
          }
        }
      }

      if (!botUsername || !startParam) {
        const [hashPath, hashQueryPart = ""] = rawHash.split("?");
        const normalizedHashPath = hashPath.replace(/^\/+/u, "");

        if (normalizedHashPath.startsWith("@")) {
          botUsername = normalizedHashPath.slice(1).split("/")[0] ?? "";
        }

        startParam = new URLSearchParams(hashQueryPart).get("start");
      }
    } else {
      botUsername = url.pathname.replace(/^\/+/u, "").split("/")[0] ?? "";
      startParam = url.searchParams.get("start");
    }

    if (!botUsername || !startParam) {
      return { webLink: deeplink };
    }

    const inner = `tg://resolve?domain=${botUsername}&start=${startParam}`;
    const normalizedWebLink = `https://web.telegram.org/k/#?tgaddr=${encodeURIComponent(inner)}`;

    return { webLink: normalizedWebLink };
  } catch {
    return { webLink: deeplink };
  }
}

const hasValidBotStart = (link: string | null) => {
  if (!link) {
    return false;
  }

  try {
    const url = new URL(link);

    if (url.hostname === "web.telegram.org") {
      const rawHash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;

      if (rawHash.startsWith("?")) {
        const hashParams = new URLSearchParams(rawHash.slice(1));
        const tgaddr = hashParams.get("tgaddr");

        if (tgaddr) {
          try {
            const decoded = decodeURIComponent(tgaddr);
            const tgUrl = new URL(decoded);
            const domain = tgUrl.searchParams.get("domain");
            const start = tgUrl.searchParams.get("start");

            return Boolean(domain && start);
          } catch {
            return false;
          }
        }

        return false;
      }

      const [hashPath, hashQueryPart = ""] = rawHash.split("?");
      const normalizedHashPath = hashPath.replace(/^\/+/u, "");

      if (!normalizedHashPath.startsWith("@")) {
        return false;
      }

      const botUsername = normalizedHashPath.slice(1).split("/")[0] ?? "";
      const startParam = new URLSearchParams(hashQueryPart).get("start");

      return Boolean(botUsername && startParam);
    }

    const botUsername = url.pathname.replace(/^\/+/u, "").split("/")[0] ?? "";
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
    loading,
    error,
    isAuthenticated,
    isInitialized,
    initFromStorage,
    stopTelegramLoginPolling,
  } = useAuthStore();

  const [localError, setLocalError] = useState<string | null>(null);
  const [qrImage, setQrImage] = useState<string | null>(null);

  const autoEnsureRef = useRef(false);

  const { webLink } = useMemo(() => buildTelegramLinks(pendingDeeplink), [pendingDeeplink]);
  const qrLink = webLink;
  const isTelegramWebLinkReady = Boolean(webLink && hasValidBotStart(webLink));

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/bots");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    let cancelled = false;

    const generateQr = async () => {
      if (!qrLink) {
        setQrImage(null);
        return;
      }

      try {
        const url = await QRCode.toDataURL(qrLink);
        if (cancelled) {
          return;
        }
        setQrImage(url);
      } catch {
        if (cancelled) {
          return;
        }
        setQrImage(null);
      }
    };

    void generateQr();

    return () => {
      cancelled = true;
    };
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
    if (!isInitialized || loading) {
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
  }, [ensurePendingLogin, isInitialized, isPendingValid, loading]);

  const getTelegramLink = useCallback(async () => {
    if (webLink && hasValidBotStart(webLink)) {
      return webLink;
    }

    const deeplink = await ensurePendingLogin();
    if (!deeplink) {
      return null;
    }

    const resolvedLinks = buildTelegramLinks(deeplink);

    return resolvedLinks.webLink;
  }, [ensurePendingLogin, webLink]);

  const handleTelegramLoginClick = useCallback(() => {
    setLocalError(null);

    if (isTelegramWebLinkReady && webLink) {
      const openedWindow = window.open(webLink, "_blank", "noopener,noreferrer");
      if (!openedWindow) {
        setLocalError("Разрешите всплывающие окна для входа через Telegram");
      }
      return;
    }

    void (async () => {
      try {
        const link = await getTelegramLink();
        if (!link) {
          return;
        }

        window.location.href = link;
      } catch {
        // Ничего не делать.
        // localError уже может быть выставлен внутри ensurePendingLogin().
      }
    })();
  }, [getTelegramLink, isTelegramWebLinkReady, webLink]);

  return (
    <LayoutShell title="Вход" description="Авторизация в ServiceAI">
      <div className={styles.screen}>
        <div className={styles.panel}>
          <div className={styles.loginGrid}>
            <div className={`${styles.tgButtonCell} ${styles.appear1}`}>
              <Button
                type="button"
                className={styles.btn}
                onClick={handleTelegramLoginClick}
                disabled={loading}
              >
                {loading
                  ? "Готовим ссылку..."
                  : isTelegramWebLinkReady
                    ? "Войти через Telegram"
                    : "Подготовить вход через Telegram"}
              </Button>
            </div>

            <div className={`${styles.tgQrCell} ${styles.appear2}`}>
              <div className={styles.qrCard}>
                {qrImage ? (
                  <img src={qrImage} alt="Telegram QR" className={styles.qrImage} />
                ) : loading ? (
                  <p className={styles.qrPlaceholder}>Готовим QR...</p>
                ) : !isTelegramWebLinkReady ? (
                  <p className={styles.qrPlaceholder}>
                    Нажмите «Подготовить вход через Telegram», чтобы получить QR
                  </p>
                ) : (
                  <p className={styles.qrPlaceholder}>Готовим QR...</p>
                )}
              </div>
            </div>

            <div className={`${styles.maxQrCell} ${styles.appear1}`}>
              <div className={styles.qrCard}>
                <p className={styles.qrPlaceholder}>QR скоро будет доступен</p>
              </div>
            </div>

            <div className={`${styles.maxButtonCell} ${styles.appear2}`}>
              <Button
                type="button"
                className={styles.btn}
                variant="secondary"
                onClick={() => setLocalError("Вход через Max скоро будет доступен")}
              >
                Войти через Max
              </Button>
            </div>
          </div>
          {(localError || error) && <p className={styles.error}>{localError || error}</p>}
        </div>
      </div>
    </LayoutShell>
  );
}
