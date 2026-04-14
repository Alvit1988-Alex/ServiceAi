"use client";

import React, { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { updateAccountProfile } from "@/app/api/accountApi";
import { useUiStore } from "../../../store/ui.store";
import { useAuthStore } from "../../../store/auth.store";
import styles from "./Topbar.module.css";

const Topbar: React.FC = () => {
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const theme = useUiStore((state) => state.theme);
  const toggleTheme = useUiStore((state) => state.toggleTheme);
  const globalLoading = useUiStore((state) => state.globalLoading);
  const lastError = useUiStore((state) => state.lastError);
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");

  const themeLabel = theme === "dark" ? "Светлая тема" : "Темная тема";
  const initials = useMemo(() => {
    const source = (user?.first_name || user?.full_name || "АК").trim();
    return source.slice(0, 2).toUpperCase();
  }, [user]);

  const copyId = async () => {
    if (!user?.account_public_id) return;
    await navigator.clipboard.writeText(user.account_public_id);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  const saveProfile = async () => {
    if (!user?.id || !firstName.trim() || !email.trim()) return;
    const updated = await updateAccountProfile(user.id, {
      first_name: firstName.trim(),
      last_name: lastName.trim() || null,
      email: email.trim(),
    });
    useAuthStore.setState({ user: updated });
    setOpen(false);
  };

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <div className={styles.brand} aria-label="Service AI">
          <span className={styles.brandAccent}>Service</span>
          <span className={styles.brandText}>AI</span>
        </div>
      </div>
      <div className={styles.actions}>
        <div className={styles.statuses}>
          {globalLoading && <span className={`${styles.status} ${styles.loading}`}>Загрузка</span>}
          {lastError && <span className={`${styles.status} ${styles.error}`}>{lastError}</span>}
        </div>
        {user?.account_public_id && (
          <div className={styles.accountIdWrap}>
            <button type="button" className={styles.accountId} onClick={copyId}>ID: {user.account_public_id}</button>
            <button
              type="button"
              className={styles.copyIconBtn}
              onClick={copyId}
              aria-label="Скопировать ID"
              title="Скопировать ID"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M9 9h10v11H9z" />
                <path d="M5 4h10v2H7v11H5z" />
              </svg>
            </button>
            {copied && <span className={styles.copied}>ID скопирован</span>}
          </div>
        )}
        <button type="button" className={styles.themeToggle} onClick={toggleTheme}>{themeLabel}</button>
        <button type="button" className={styles.avatar} onClick={() => setOpen((v) => !v)}>{initials}</button>
        {open && (
          <div className={styles.panel}>
            <p className={styles.panelTitle}>Настройки аккаунта</p>
            <input className={styles.field} placeholder="Имя *" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <input className={styles.field} placeholder="Фамилия (необязательно)" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            <input className={styles.field} placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button className={styles.copyBtn} type="button" onClick={saveProfile}>Сохранить</button>
          </div>
        )}
        <button
          className={styles.logout}
          type="button"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
        >
          Выход
        </button>
      </div>
    </header>
  );
};

export default Topbar;
