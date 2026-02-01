"use client";

import { FormEvent, useEffect, useState } from "react";

import { getCurrentAccount, updateAccountProfile } from "@/app/api/accountApi";
import { AccountProfile } from "@/app/api/types";
import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";
import { useAuthStore } from "@/store/auth.store";

import styles from "./settings.module.css";

export default function SettingsPage() {
  const authUser = useAuthStore((state) => state.user);

  const [account, setAccount] = useState<AccountProfile | null>(authUser);
  const [profileForm, setProfileForm] = useState({
    full_name: authUser?.full_name ?? "",
    email: authUser?.email ?? "",
  });
  const [profileLoading, setProfileLoading] = useState(!authUser);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (authUser) {
      setAccount(authUser);
      setProfileForm({
        full_name: authUser.full_name ?? "",
        email: authUser.email,
      });
      setProfileLoading(false);
      return;
    }

    void loadAccountProfile();
  }, [authUser]);

  async function loadAccountProfile() {
    setProfileLoading(true);
    setProfileError(null);

    try {
      const profile = await getCurrentAccount();
      setAccount(profile);
      setProfileForm({
        full_name: profile.full_name ?? "",
        email: profile.email,
      });
      useAuthStore.setState({ user: profile });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось загрузить профиль";
      setProfileError(message);
    } finally {
      setProfileLoading(false);
    }
  }

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileError(null);
    setProfileSuccess(null);

    if (!profileForm.full_name.trim() || !profileForm.email.trim()) {
      setProfileError("Заполните все поля профиля");
      return;
    }

    if (!account?.id) {
      setProfileError("Не удалось определить пользователя для обновления");
      return;
    }

    setProfileLoading(true);

    try {
      const updated = await updateAccountProfile(account.id, {
        full_name: profileForm.full_name.trim(),
        email: profileForm.email.trim(),
      });
      setAccount(updated);
      useAuthStore.setState({ user: updated });
      setProfileSuccess("Профиль успешно обновлен");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось обновить профиль";
      setProfileError(message);
    } finally {
      setProfileLoading(false);
    }
  }

  return (
    <AuthGuard>
      <LayoutShell
        title="Настройки аккаунта"
        description="Обновите данные профиля, чтобы поддерживать актуальную информацию."
      >
        <div className={styles.page}>
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <p className={styles.eyebrow}>Профиль</p>
                <h2 className={styles.sectionTitle}>Личные данные</h2>
              </div>
              {profileLoading && <span className={styles.muted}>Загружаем профиль...</span>}
            </div>

            <form className={styles.form} onSubmit={handleProfileSubmit}>
              <label className={styles.field}>
                <span className={styles.label}>Имя и фамилия</span>
                <input
                  className={styles.input}
                  name="full_name"
                  type="text"
                  value={profileForm.full_name}
                  onChange={(event) =>
                    setProfileForm((prev) => ({ ...prev, full_name: event.target.value }))
                  }
                  disabled={profileLoading}
                  placeholder="Введите имя"
                />
              </label>

              <label className={styles.field}>
                <span className={styles.label}>Email</span>
                <input
                  className={styles.input}
                  name="email"
                  type="email"
                  value={profileForm.email}
                  onChange={(event) => setProfileForm((prev) => ({ ...prev, email: event.target.value }))}
                  disabled={profileLoading}
                  placeholder="example@domain.com"
                />
              </label>

              <div className={styles.actions}>
                <button className={styles.button} type="submit" disabled={profileLoading}>
                  {profileLoading ? "Сохраняем..." : "Сохранить"}
                </button>
              </div>

              {profileError && <p className={styles.error}>{profileError}</p>}
              {profileSuccess && <p className={styles.success}>{profileSuccess}</p>}
            </form>
          </section>
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
