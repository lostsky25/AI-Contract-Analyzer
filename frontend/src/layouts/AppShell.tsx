import type { PropsWithChildren } from "react";

type AppShellProps = PropsWithChildren<{
  backendHealthy: boolean;
}>;

export function AppShell({ backendHealthy, children }: AppShellProps) {
  return (
    <div className="app-bg">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">AI Contract Analyzer</p>
            <h1>Frontend MVP</h1>
          </div>
          <span className={backendHealthy ? "health ok" : "health down"}>
            {backendHealthy ? "Backend online" : "Backend offline"}
          </span>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
