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

  const { webLink } = useMemo(
    () => buildTelegramLinks(pendingDeeplink),
    [pendingDeeplink],
  );
  const qrLink = webLink;

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

  return (
    <LayoutShell title="Вход" description="Авторизация в ServiceAI">
      <div className={styles.screen}>
        <div className={styles.panel}>
          <div className={styles.buttons}>
            <div className={styles.appear1}>
              <Button
                type="button"
                className={styles.btn}
                onClick={async () => {
                  await openExternalLink(getTelegramWebLink);
                }}
                disabled={loading}
              >
                {loading ? "Готовим ссылку..." : "Войти через Telegram"}
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
