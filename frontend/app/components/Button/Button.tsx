import { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ className = "", ...props }: ButtonProps) {
  const classNames = [styles.button, className].filter(Boolean).join(" ");

  return <button className={classNames} {...props} />;
}
