import { FormEvent, useMemo, useState } from "react";

import {
  ApiError,
  apiClient,
  saveAuthToken
} from "../services/api";
import type { UserResponse } from "../types/api";

type AuthMode = "login" | "register";

type AuthPageProps = {
  onAuthenticated: (user: UserResponse) => void;
};

function parseError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Не удалось выполнить запрос";
}

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const title = useMemo(
    () => (mode === "login" ? "Вход в аккаунт" : "Регистрация"),
    [mode]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === "register") {
        await apiClient.register({
          username,
          email,
          password
        });
      }

      const auth = await apiClient.login({ username, password });
      saveAuthToken(auth.access_token);
      onAuthenticated(auth.user);
    } catch (errorValue) {
      setError(parseError(errorValue));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="app-bg">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="shell auth-shell">
        <article className="card auth-card reveal">
          <div className="section-head">
            <h2>{title}</h2>
            <button
              className="button ghost"
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
            >
              {mode === "login" ? "Создать аккаунт" : "У меня уже есть аккаунт"}
            </button>
          </div>

          {error ? <p className="alert">{error}</p> : null}

          <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
            <label>
              Username
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                minLength={3}
              />
            </label>

            {mode === "register" ? (
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </label>
            ) : null}

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={6}
              />
            </label>

            <button className="button primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Подождите..." : mode === "login" ? "Войти" : "Зарегистрироваться"}
            </button>
          </form>
        </article>
      </div>
    </div>
  );
}
