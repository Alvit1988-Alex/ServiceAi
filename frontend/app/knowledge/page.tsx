"use client";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";

export default function KnowledgePage() {
  return (
    <AuthGuard>
      <LayoutShell title="ИИ и база знаний" description="Настройка ИИ и базы знаний.">
        <div style={{ display: "flex", justifyContent: "center", padding: "2rem 0" }}>
          <p>Раздел в разработке</p>
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
