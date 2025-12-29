"use client";

import { useEffect } from "react";

import { useUiStore } from "@/store/ui.store";

const FORCE_THEME = "dark";

const ForceTheme = () => {
  const setThemeForced = useUiStore((state) => state.setThemeForced);
  const restoreTheme = useUiStore((state) => state.restoreTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", FORCE_THEME);
    root.setAttribute("data-theme-forced", FORCE_THEME);
    setThemeForced(FORCE_THEME);

    return () => {
      root.removeAttribute("data-theme-forced");
      restoreTheme();
    };
  }, [restoreTheme, setThemeForced]);

  return null;
};

export default ForceTheme;
