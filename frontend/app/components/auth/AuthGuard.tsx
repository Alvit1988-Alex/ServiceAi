"use client";

import { useRouter, usePathname } from "next/navigation";
import { PropsWithChildren, useEffect } from "react";

import { useAuthStore } from "@/store/auth.store";

/**
 * Хук, который:
 * 1) один раз инициализирует auth из localStorage;
 * 2) после инициализации делает нужные редиректы.
 */
export function useAuthGuard() {
  const router = useRouter();
  const pathname = usePathname();

  const initFromStorage = useAuthStore((s) => s.initFromStorage);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isInitialized = useAuthStore((s) => s.isInitialized);

  // Инициализация из localStorage
  useEffect(() => {
    if (!isInitialized) {
      void initFromStorage();
    }
  }, [isInitialized, initFromStorage]);

  // Редиректы после инициализации
  useEffect(() => {
    if (!isInitialized) return;

    const isLoginPage = pathname === "/login";

    // Не авторизован и не на /login → отправляем на /login
    if (!isAuthenticated && !isLoginPage) {
      router.replace("/login");
      return;
    }

    // Авторизован и на /login → отправляем на главную
    if (isAuthenticated && isLoginPage) {
      router.replace("/");
    }
  }, [isAuthenticated, isInitialized, pathname, router]);
}

export function AuthGuard({ children }: PropsWithChildren) {
  const isInitialized = useAuthStore((s) => s.isInitialized);

  useAuthGuard();

  if (!isInitialized) {
    return <p>Загрузка...</p>;
  }

  return <>{children}</>;
}
