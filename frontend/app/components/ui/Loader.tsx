import styles from "./Loader.module.css";

type LoaderProps = {
  className?: string;
};

export function Loader({ className = "" }: LoaderProps) {
  const classNames = [styles.loader, className].filter(Boolean).join(" ");

  return <span className={classNames} role="status" aria-live="polite" />;
}
