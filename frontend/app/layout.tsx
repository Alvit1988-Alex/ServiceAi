import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";
import AppShell from "./components/layout/AppShell";
import ThemeBootstrap from "./components/ThemeBootstrap";

const themeScript = `
(() => {
  try {
    const stored = localStorage.getItem("serviceai_theme");
    const theme =
      stored === "light" || stored === "dark"
        ? stored
        : window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
    document.documentElement.setAttribute("data-theme", theme);
  } catch (error) {
    // no-op
  }
})();
`;

export const metadata: Metadata = {
  title: "ServiceAI",
  description: "ServiceAI admin panel",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>
          <ThemeBootstrap />
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
