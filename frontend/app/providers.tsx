"use client";
import type { PropsWithChildren } from "react";

import { DialogsEventsProvider } from "./components/dialogs/DialogsEventsProvider";

export default function Providers({ children }: PropsWithChildren) {
  return <DialogsEventsProvider>{children}</DialogsEventsProvider>;
}
