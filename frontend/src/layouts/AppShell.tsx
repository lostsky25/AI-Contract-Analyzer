import type { PropsWithChildren, ReactNode } from "react";

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
  icon: ReactNode;
};

const NAV_ITEMS: NavItem[] = [
  {
    id: "home",
    label: "Главная",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M3 11.5L12 4l9 7.5v8a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" fill="currentColor" />
      </svg>
    )
  },
  {
    id: "documents",
    label: "Документы",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path
          d="M7 3h7l5 5v12.5A1.5 1.5 0 0 1 17.5 22h-11A1.5 1.5 0 0 1 5 20.5v-16A1.5 1.5 0 0 1 6.5 3zm6 1.5V9h4.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  },
  {
    id: "reports",
    label: "Отчёты",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path
          d="M5 5.5A1.5 1.5 0 0 1 6.5 4h11A1.5 1.5 0 0 1 19 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 18.5zm4 2.5h6m-6 4h6m-6 4h3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  }
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
            <div className="sidebar-user-head">
              <div className="user-avatar">{(userLabel?.[0] ?? "A").toUpperCase()}</div>
              <div className="user-meta">
                <strong>{userLabel ?? "Alex"}</strong>
                <span>{userLabel ? `${userLabel.toLowerCase()}@app.local` : "alex@app.local"}</span>
              </div>
              <span className="user-caret" aria-hidden>
                v
              </span>
            </div>
            {onLogout ? (
              <button className="button ghost sidebar-logout" onClick={onLogout} type="button">
                <span aria-hidden>-&gt;</span>
                Выйти
              </button>
            ) : null}
          </div>
        </aside>

        <div className="workspace">
          <header className={`workspace-topbar ${searchEnabled ? "" : "no-search"}`}>
            {searchEnabled ? (
              <div className="search-wrap">
                <span className="search-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" />
                    <path d="M16 16l5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </span>
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
                <span aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path
                      d="M12 4a5 5 0 0 1 5 5v3.5l1.6 2.4a1 1 0 0 1-.8 1.6H6.2a1 1 0 0 1-.8-1.6L7 12.5V9a5 5 0 0 1 5-5zm0 15a2.2 2.2 0 0 0 2-1.3h-4A2.2 2.2 0 0 0 12 19z"
                      fill="currentColor"
                    />
                  </svg>
                </span>
              </button>
              <button className="icon-btn" type="button" aria-label="Help">
                <span aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.8" />
                    <path
                      d="M9.8 9.4a2.4 2.4 0 1 1 3.2 2.2c-.8.3-1.2.8-1.2 1.6v.3m1.2 3.1h.1"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
              </button>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}
