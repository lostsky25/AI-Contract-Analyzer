import type { PropsWithChildren } from "react";

type StepCardProps = PropsWithChildren<{
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
  disabled?: boolean;
  loading?: boolean;
  done?: boolean;
}>;

export function StepCard({
  title,
  description,
  actionLabel,
  onAction,
  disabled,
  loading,
  done,
  children
}: StepCardProps) {
  return (
    <article className="card step-card reveal">
      <header className="step-card-header">
        <h3>{title}</h3>
        {done ? <span className="done-mark">Готово</span> : null}
      </header>
      <p className="muted">{description}</p>
      {children}
      <button className="button primary" onClick={onAction} disabled={disabled || loading}>
        {loading ? "Выполняется..." : actionLabel}
      </button>
    </article>
  );
}
