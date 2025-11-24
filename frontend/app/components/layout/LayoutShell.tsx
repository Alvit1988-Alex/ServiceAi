import type { ReactNode } from "react";
import styles from "./LayoutShell.module.css";

interface LayoutShellProps {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

export default function LayoutShell({
  title,
  description,
  actions,
  children,
}: LayoutShellProps) {
  const hasHeader = title || description || actions;

  return (
    <section className={styles.shell}>
      <div className={styles.inner}>
        {hasHeader && (
          <header className={styles.header}>
            <div className={styles.heading}>
              {title && <h1 className={styles.title}>{title}</h1>}
              {description && (
                <p className={styles.description}>{description}</p>
              )}
            </div>
            {actions && <div className={styles.actions}>{actions}</div>}
          </header>
        )}

        <div className={styles.content}>{children}</div>
      </div>
    </section>
  );
}
