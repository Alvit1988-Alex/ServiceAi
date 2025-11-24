"use client";

import styles from "./Tabs.module.css";

export interface TabItem {
  value: string;
  label: string;
  disabled?: boolean;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (value: string) => void;
  className?: string;
}

export default function Tabs({ tabs, activeTab, onTabChange, className }: TabsProps) {
  const containerClassName = className ? `${styles.tabs} ${className}` : styles.tabs;

  return (
    <div className={containerClassName}>
      {tabs.map((tab) => {
        const isActive = tab.value === activeTab;
        const tabClassName = [styles.tab];
        if (isActive) {
          tabClassName.push(styles.active);
        }
        if (tab.disabled) {
          tabClassName.push(styles.disabled);
        }

        return (
          <button
            key={tab.value}
            type="button"
            className={tabClassName.join(" ")}
            onClick={() => !tab.disabled && onTabChange(tab.value)}
            disabled={tab.disabled}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
