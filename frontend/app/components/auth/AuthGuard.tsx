"use client";

import { useRouter } from "next/navigation";
import { PropsWithChildren, useEffect } from "react";

import { useAuthStore } from "@/store/auth.store";

export function useAuthGuard() {
  const router = useRouter();
  const { isAuthenticated, isInitialized, initFromStorage } = useAuthStore();

  useEffect(() => {
    void initFromStorage();
  }, [initFromStorage]);

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isInitialized, router]);
}

export function AuthGuard({ children }: PropsWithChildren) {
  const { isInitialized } = useAuthStore();
  useAuthGuard();

  if (!isInitialized) {
    return <p>Загрузка...</p>;
  }

  return <>{children}</>;
}
