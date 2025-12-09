"use client";

import type { PropsWithChildren } from "react";

import { Sidebar } from "./Sidebar";
import Topbar from "./Topbar";

/**
 * Каркас приложения:
 * — слева сайдбар
 * — справа контент с топбаром и основным содержимым.
 * Без zustand, без useEffect, только верстка.
 */
export default function AppShell({ children }: PropsWithChildren) {
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
