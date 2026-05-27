import type { PropsWithChildren } from "react";

type AppShellProps = PropsWithChildren<{
  backendHealthy: boolean;
  userLabel?: string;
  onLogout?: () => void;
}>;

export function AppShell({ backendHealthy, userLabel, onLogout, children }: AppShellProps) {
  return (
    <div className="app-bg">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">AI Contract Analyzer</p>
            <h1>Frontend MVP</h1>
            {userLabel ? <p className="muted topbar-user">Пользователь: {userLabel}</p> : null}
          </div>
          <div className="topbar-actions">
            <span className={backendHealthy ? "health ok" : "health down"}>
              {backendHealthy ? "Backend online" : "Backend offline"}
            </span>
            {onLogout ? (
              <button className="button ghost" onClick={onLogout} type="button">
                Выйти
              </button>
            ) : null}
          </div>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
