import { useEffect, useState } from "react";

import { DashboardPage } from "./pages/DashboardPage";
import { AuthPage } from "./pages/AuthPage";
import { ApiError, apiClient, clearAuthToken, hasAuthToken } from "./services/api";
import type { UserResponse } from "./types/api";

function App() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function bootstrapAuth() {
      if (!hasAuthToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await apiClient.getMe();
        setUser(me);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearAuthToken();
        }
      } finally {
        setIsLoading(false);
      }
    }
    void bootstrapAuth();
  }, []);

  if (isLoading) {
    return (
      <div className="app-bg">
        <div className="shell">
          <p className="muted">Проверка авторизации...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthPage onAuthenticated={setUser} />;
  }

  return (
    <DashboardPage
      currentUsername={user.username}
      onLogout={() => {
        clearAuthToken();
        setUser(null);
      }}
    />
  );
}

export default App;
