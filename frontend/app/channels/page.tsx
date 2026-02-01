"use client";

import { AuthGuard } from "@/app/components/auth/AuthGuard";
import LayoutShell from "@/app/components/layout/LayoutShell";

export default function ChannelsPage() {
  return (
    <AuthGuard>
      <LayoutShell title="Каналы" description="Управление каналами.">
        <div style={{ display: "flex", justifyContent: "center", padding: "2rem 0" }}>
          <p>Раздел в разработке</p>
        </div>
      </LayoutShell>
    </AuthGuard>
  );
}
