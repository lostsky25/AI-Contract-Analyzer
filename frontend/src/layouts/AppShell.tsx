import type { PropsWithChildren } from "react";

type NavAction = "home" | "documents" | "reports";

type AppShellProps = PropsWithChildren<{
  backendHealthy: boolean;
  userLabel?: string;
  onLogout?: () => void;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  searchEnabled?: boolean;
  activeSection: "home" | "documents" | "reports";
  onNavigate: (target: NavAction) => void;
}>;

type NavItem = {
  id: NavAction;
  label: string;
  icon: string;
};

const NAV_ITEMS: NavItem[] = [
  { id: "home", label: "Главная", icon: "⌂" },
  { id: "documents", label: "Документы", icon: "▦" },
  { id: "reports", label: "Отчеты", icon: "▤" }
];

export function AppShell({
  backendHealthy,
  userLabel,
  onLogout,
  searchQuery,
  onSearchChange,
  searchEnabled = false,
  activeSection,
  onNavigate,
  children
}: AppShellProps) {
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
            {NAV_ITEMS.map((item) => {
              const active = item.id === activeSection;
              return (
                <button
                  key={item.id}
                  className={`sidebar-nav-item ${active ? "active" : ""}`}
                  type="button"
                  onClick={() => onNavigate(item.id)}
                >
                  <span className="sidebar-nav-icon">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              );
            })}
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
          <header className={`workspace-topbar ${searchEnabled ? "" : "no-search"}`}>
            {searchEnabled ? (
              <div className="search-wrap">
                <span className="search-icon">⌕</span>
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(event) => onSearchChange(event.target.value)}
                  placeholder="Поиск по последним документам..."
                  aria-label="Поиск документов"
                />
                {searchQuery ? (
                  <button
                    className="clear-search-btn"
                    type="button"
                    onClick={() => onSearchChange("")}
                    aria-label="Очистить поиск"
                  >
                    Очистить
                  </button>
                ) : null}
              </div>
            ) : null}
            <div className="topbar-right">
              <span className={backendHealthy ? "health ok" : "health down"}>
                {backendHealthy ? "Backend online" : "Backend offline"}
              </span>
              <button className="icon-btn" type="button" aria-label="Notifications">
                ⦿
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
