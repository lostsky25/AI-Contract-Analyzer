import type { PropsWithChildren } from "react";

type AppShellProps = PropsWithChildren<{
  backendHealthy: boolean;
  userLabel?: string;
  onLogout?: () => void;
}>;

const NAV_ITEMS = ["Главная", "Документы", "Отчеты", "История", "Настройки"];

export function AppShell({ backendHealthy, userLabel, onLogout, children }: AppShellProps) {
  return (
    <div className="app-bg">
      <div className="app-layout">
        <aside className="dashboard-sidebar">
          <div className="sidebar-brand">
            <div className="brand-icon">AI</div>
            <div>
              <p className="brand-title">AI Contract</p>
              <p className="brand-title">Analyzer</p>
            </div>
          </div>

          <nav className="sidebar-nav">
            {NAV_ITEMS.map((item, index) => (
              <button
                key={item}
                className={`sidebar-nav-item ${index === 0 ? "active" : ""}`}
                type="button"
              >
                <span className="sidebar-nav-icon">{index === 0 ? "⌂" : "○"}</span>
                <span>{item}</span>
              </button>
            ))}
          </nav>

          <div className="sidebar-user">
            <div className="user-avatar">{(userLabel?.[0] ?? "U").toUpperCase()}</div>
            <div className="user-meta">
              <strong>{userLabel ?? "Пользователь"}</strong>
              <span>{userLabel ? `${userLabel}@app.local` : "user@app.local"}</span>
            </div>
            {onLogout ? (
              <button className="button ghost sidebar-logout" onClick={onLogout} type="button">
                Выйти
              </button>
            ) : null}
          </div>
        </aside>

        <div className="workspace">
          <header className="workspace-topbar">
            <div className="search-wrap">
              <span className="search-icon">⌕</span>
              <input
                type="search"
                placeholder="Поиск по документам, отчетам и вопросам..."
                aria-label="Search"
              />
            </div>
            <div className="topbar-right">
              <span className={backendHealthy ? "health ok" : "health down"}>
                {backendHealthy ? "Backend online" : "Backend offline"}
              </span>
              <button className="icon-btn" type="button" aria-label="Notifications">
                🔔
              </button>
              <button className="icon-btn" type="button" aria-label="Help">
                ?
              </button>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}
