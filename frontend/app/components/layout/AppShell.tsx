"use client";

import type { PropsWithChildren } from "react";
import { usePathname } from "next/navigation";

import { Sidebar } from "./Sidebar";
import Topbar from "./Topbar";

/**
 * Каркас приложения:
 * — слева сайдбар
 * — справа контент с топбаром и основным содержимым.
 * Без zustand, без useEffect, только верстка.
 */
export default function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname.startsWith("/login/");
  const isEmbedPage = pathname === "/embed" || pathname.startsWith("/embed/");

  if (isAuthPage || isEmbedPage) {
    return (
      <div style={{ height: "100vh", minHeight: "100vh" }}>
        <main style={{ height: "100vh", minHeight: "100vh" }}>{children}</main>
      </div>
    );
  }

  return (
    <div className="app-layout" style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div className="content" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Topbar />
        <main className="main-content" style={{ flex: 1 }}>
          {children}
        </main>
      </div>
    </div>
  );
}
