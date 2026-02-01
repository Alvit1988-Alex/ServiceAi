import type { ReactNode } from "react";

import ForceTheme from "./force-theme";

const forcedThemeScript = `
(() => {
  try {
    document.documentElement.setAttribute("data-theme", "light");
    document.documentElement.setAttribute("data-theme-forced", "light");
  } catch (error) {
    // no-op
  }
})();
`;

export default function LoginLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <head>
        <script dangerouslySetInnerHTML={{ __html: forcedThemeScript }} />
      </head>
      <ForceTheme />
      {children}
    </>
  );
}
