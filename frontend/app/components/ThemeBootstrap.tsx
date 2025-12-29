"use client";

import { useEffect } from "react";

import { useUiStore } from "../../store/ui.store";

const ThemeBootstrap = () => {
  const initTheme = useUiStore((state) => state.initTheme);

  useEffect(() => {
    initTheme();
  }, [initTheme]);

  return null;
};

export default ThemeBootstrap;
