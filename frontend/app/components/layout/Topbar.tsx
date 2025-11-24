import React from "react";
import styles from "./Topbar.module.css";

const Topbar: React.FC = () => {
  return (
    <header className={styles.topbar}>
      <div className={styles.title}>Панель управления</div>
      <div className={styles.actions}>
        <button type="button" className={styles.themeToggle}>
          Тема
        </button>
        <div className={styles.avatar}>АК</div>
      </div>
    </header>
  );
};

export default Topbar;
