"use client";

import { PropsWithChildren, useEffect } from "react";

import { useUiStore } from "@/store/ui.store";

import { Sidebar } from "./Sidebar";
import Topbar from "./Topbar";

export default function AppShell({ children }: PropsWithChildren) {
  const { initUi, sidebarCollapsed } = useUiStore((state) => ({
    initUi: state.initUi,
    sidebarCollapsed: state.sidebarCollapsed,
  }));

  useEffect(() => {
    initUi();
  }, [initUi]);

  return (
    <div className="app-layout" data-collapsed={sidebarCollapsed}>
      <Sidebar />
      <div className="content">
        <Topbar />
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
