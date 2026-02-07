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
    return { webLink: null, tgLink: null };
  }

  try {
    const url = new URL(deeplink);
    const botUsername = url.pathname.replace(/^\/+/u, "").split("/")[0] ?? "";
    const startParam = url.searchParams.get("start");

    if (url.hostname === "telegram.me") {
      url.hostname = "t.me";
    }

    if (!botUsername || !startParam) {
      return { webLink: deeplink, tgLink: null };
    }

    const normalizedWebLink = `https://t.me/${botUsername}?start=${encodeURIComponent(startParam)}`;
    const tgLink = `tg://resolve?domain=${encodeURIComponent(botUsername)}&start=${encodeURIComponent(startParam)}`;

    return {
      webLink: normalizedWebLink,
      tgLink,
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

    if (url.protocol === "tg:") {
      const botUsername = url.searchParams.get("domain");
      const startParam = url.searchParams.get("start");
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

  const autoEnsureRef = useRef(false);
  const qrImageRef = useRef<string | null>(null);

  const { webLink, tgLink } = useMemo(
    () => buildTelegramLinks(pendingDeeplink),
    [pendingDeeplink],
  );
  const qrLink = webLink;
  const isTelegramLinkReady = Boolean(tgLink && hasValidBotStart(tgLink));

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/bots");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    const generateQr = async () => {
      if (!qrLink) {
        qrImageRef.current = null;
        return;
      }
      try {
        const url = await QRCode.toDataURL(qrLink);
        qrImageRef.current = url;
      } catch {
        qrImageRef.current = null;
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

  const getTelegramWebLink = useCallback(async () => {
    if (tgLink && hasValidBotStart(tgLink)) {
      return tgLink;
    }

    if (webLink && hasValidBotStart(webLink)) {
      return webLink;
    }

    const deeplink = await ensurePendingLogin();
    if (!deeplink) {
      return null;
    }
    const resolvedLinks = buildTelegramLinks(deeplink);

    if (resolvedLinks.tgLink && hasValidBotStart(resolvedLinks.tgLink)) {
      return resolvedLinks.tgLink;
    }

    return resolvedLinks.webLink;
  }, [ensurePendingLogin, tgLink, webLink]);

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

    if (link.startsWith("tg://")) {
      if (w) {
        w.location.href = link;
        w.focus?.();
      } else {
        window.location.href = link;
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

  const handleTelegramLoginClick = useCallback(() => {
    if (tgLink && hasValidBotStart(tgLink)) {
      window.location.assign(tgLink);
      return;
    }

    void ensurePendingLogin();
  }, [ensurePendingLogin, tgLink]);

  return (
    <LayoutShell title="Вход" description="Авторизация в ServiceAI">
      <div className={styles.screen}>
        <div className={styles.panel}>
          <div className={styles.buttons}>
            <div className={styles.appear1}>
              <Button
                type="button"
                className={styles.btn}
                onClick={handleTelegramLoginClick}
                disabled={loading}
              >
                {loading ? "Готовим ссылку..." : isTelegramLinkReady ? "Войти через Telegram" : "Подготовить вход через Telegram"}
              </Button>
            </div>
            <div className={styles.appear2}>
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
