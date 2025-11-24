"use client";

import { PropsWithChildren } from "react";

import { DialogsEventsProvider } from "@/app/components/dialogs/DialogsEventsProvider";

export default function Providers({ children }: PropsWithChildren) {
  return <DialogsEventsProvider>{children}</DialogsEventsProvider>;
}
