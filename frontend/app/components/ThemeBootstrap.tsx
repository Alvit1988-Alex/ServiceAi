"use client";

import { useEffect } from "react";

import { useUiStore } from "../../store/ui.store";

const ThemeBootstrap = () => {
  const initTheme = useUiStore((state) => state.initTheme);
  const setThemeForced = useUiStore((state) => state.setThemeForced);

  useEffect(() => {
    const forcedTheme = document.documentElement.getAttribute("data-theme-forced");
    if (forcedTheme === "light" || forcedTheme === "dark") {
      setThemeForced(forcedTheme);
      return;
    }

    initTheme();
  }, [initTheme, setThemeForced]);

  return null;
};

export default ThemeBootstrap;
