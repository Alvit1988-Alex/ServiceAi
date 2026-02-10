"use client";

import type { PropsWithChildren } from "react";
import { usePathname } from "next/navigation";

import AppTabs from "./AppTabs";
import Topbar from "./Topbar";

/**
 * Каркас приложения:
 * — сверху топбар
 * — ниже основное содержимое.
 * Без zustand, без useEffect, только верстка.
 */
export default function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname.startsWith("/login/");
  const isEmbedPage = pathname === "/embed" || pathname.startsWith("/embed/");
  const isBotsListPage = pathname === "/bots";

  if (isAuthPage || isEmbedPage) {
    return (
      <div style={{ height: "100vh", minHeight: "100vh" }}>
        <main style={{ height: "100vh", minHeight: "100vh" }}>{children}</main>
      </div>
    );
  }

  return (
    <div className="app-layout" style={{ display: "flex", minHeight: "100vh" }}>
      <div className="content" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Topbar />
        <main className="main-content" style={{ flex: 1 }}>
          <div className="page-frame">
            {!isBotsListPage && <AppTabs />}
            <div className="page-frame-body">{children}</div>
          </div>
        </main>
      </div>
    </div>
  );
}
