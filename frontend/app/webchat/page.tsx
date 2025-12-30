import { Suspense } from "react";

import WebchatClient from "./WebchatClient";

export default function WebchatPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-gray-50 p-6 text-gray-800">
          <div className="text-sm text-gray-600">Загрузка...</div>
        </main>
      }
    >
      <WebchatClient />
    </Suspense>
  );
}
