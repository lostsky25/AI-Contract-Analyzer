import type {
  AnalyzeRequest,
  AuthResponse,
  ContractReport,
  DocumentQuestionResponse,
  DocumentResponse,
  DocumentStatusResponse,
  HealthResponse,
  LegacyAnalyzeResponse,
  LegalSource,
  LegalSourcesResponse,
  LoginRequest,
  ProcessRequest,
  ProcessResponse,
  RegisterRequest,
  UploadResponse,
  UserResponse
} from "../types/api";

function normalizeApiBaseUrl(rawUrl: string): string {
  const trimmed = rawUrl.replace(/\/+$/, "");
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api"
);
const AUTH_TOKEN_KEY = "auth_token";

class ApiError extends Error {
  status?: number;
  kind?: "timeout" | "http";

  constructor(message: string, status?: number, kind: "timeout" | "http" = "http") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
  }
}

function isEndpointUnavailable(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    typeof error.status === "number" &&
    [404, 405, 501].includes(error.status)
  );
}

function normalizeError(payload: unknown): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (entry && typeof entry === "object" && "msg" in entry) {
            return String((entry as { msg: unknown }).msg);
          }
          return JSON.stringify(entry);
        })
        .join("; ");
    }
  }
  return "Не удалось выполнить запрос к серверу";
}

type RequestInitWithTimeout = RequestInit & {
  timeoutMs?: number;
  retry?: number;
  retryDelayMs?: number;
};

async function request<T>(path: string, init?: RequestInitWithTimeout): Promise<T> {
  const retry = init?.retry ?? 0;
  const retryDelayMs = init?.retryDelayMs ?? 800;
  const timeoutMs = init?.timeoutMs ?? 30000;

  const requestInit: RequestInit = { ...(init ?? {}) };
  delete (requestInit as RequestInitWithTimeout).timeoutMs;
  delete (requestInit as RequestInitWithTimeout).retry;
  delete (requestInit as RequestInitWithTimeout).retryDelayMs;

  let attempt = 0;
  while (true) {
    try {
      return await requestOnce<T>(path, requestInit, timeoutMs);
    } catch (error) {
      if (attempt >= retry) {
        throw error;
      }
      attempt += 1;
      await new Promise((resolve) => window.setTimeout(resolve, retryDelayMs));
    }
  }
}

async function requestOnce<T>(path: string, requestInit: RequestInit, timeoutMs: number): Promise<T> {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const headers = new Headers(requestInit.headers ?? {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestInit,
      headers,
      signal: controller.signal
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("REQUEST_TIMEOUT", undefined, "timeout");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as unknown;
      message = normalizeError(payload);
    } catch {
      // Keep fallback status message.
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export const apiClient = {
  getHealth() {
    return request<HealthResponse>("/health", { timeoutMs: 25000 });
  },

  uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<UploadResponse>("/upload", {
      method: "POST",
      body: formData,
      timeoutMs: 60000
    });
  },

  processDocument(payload: ProcessRequest) {
    return request<ProcessResponse>("/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      timeoutMs: 240000
    });
  },

  analyzeText(payload: AnalyzeRequest) {
    return request<LegacyAnalyzeResponse>("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      timeoutMs: 360000
    });
  },

  async analyzeDocument(
    documentId: string,
    options?: {
      legacyText?: string;
      preferOrchestrator?: boolean;
      legalWebSearchEnabled?: boolean;
    }
  ) {
    const legalWebSearchEnabled = options?.legalWebSearchEnabled ?? true;
    const analyzeBody = JSON.stringify({
      legal_web_search_enabled: legalWebSearchEnabled
    });
    const orchestrateBody = JSON.stringify({
      document_id: documentId,
      legal_web_search_enabled: legalWebSearchEnabled
    });
    const variants: Array<() => Promise<ContractReport | LegacyAnalyzeResponse>> = [];

    if (options?.preferOrchestrator) {
      variants.push(() =>
        request<ContractReport>("/orchestrate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: orchestrateBody,
          timeoutMs: 360000
        })
      );
    }

    variants.push(
      () =>
        request<ContractReport>(`/documents/${documentId}/analyze`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: analyzeBody,
          timeoutMs: 360000
        }),
      () =>
        request<ContractReport>("/orchestrate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: orchestrateBody,
          timeoutMs: 360000
        }),
      () =>
        request<LegacyAnalyzeResponse>("/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ document_id: documentId }),
          timeoutMs: 360000
        })
    );

    if (options?.legacyText?.trim()) {
      variants.push(() =>
        request<LegacyAnalyzeResponse>("/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            document_id: documentId,
            text: options.legacyText
          }),
          timeoutMs: 360000
        })
      );
    }

    let lastError: unknown;
    for (const run of variants) {
      try {
        return await run();
      } catch (error) {
        lastError = error;
        if (!isEndpointUnavailable(error)) {
          throw error;
        }
      }
    }

    throw lastError ?? new ApiError("Не удалось запустить анализ", 500);
  },

  async getDocumentStatus(documentId: string) {
    try {
      const status = await request<DocumentStatusResponse>(
        `/documents/${documentId}/status`,
        { timeoutMs: 25000 }
      );
      return request<DocumentResponse>(`/documents/${documentId}`, { timeoutMs: 25000 }).then((doc) => ({
        ...doc,
        status: status.status
      }));
    } catch (error) {
      if (isEndpointUnavailable(error)) {
        return request<DocumentResponse>(`/documents/${documentId}`, { timeoutMs: 25000 });
      }
      throw error;
    }
  },

  async fetchExistingReport(documentId: string) {
    try {
      return await request<ContractReport>(`/documents/${documentId}/report`, {
        timeoutMs: 60000,
        retry: 1,
        retryDelayMs: 1000
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        throw new ApiError("Отчет для этого документа пока не сформирован.", 404);
      }
      if (error instanceof ApiError && error.kind === "timeout") {
        throw new ApiError(
          "Отчет формируется дольше обычного. Попробуйте обновить через несколько секунд.",
          undefined,
          "timeout"
        );
      }
      throw error;
    }
  },

  async getDocumentReport(documentId: string) {
    return this.fetchExistingReport(documentId);
  },

  async askDocumentQuestion(documentId: string, question: string) {
    const body = JSON.stringify({ question });

    const variants: Array<() => Promise<DocumentQuestionResponse>> = [
      () =>
        request<DocumentQuestionResponse>(`/documents/${documentId}/ask`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body,
          timeoutMs: 120000
        })
    ];

    let lastError: unknown;
    for (const run of variants) {
      try {
        return await run();
      } catch (error) {
        lastError = error;
        if (!isEndpointUnavailable(error)) {
          throw error;
        }
      }
    }

    throw lastError ?? new ApiError("Q&A endpoint недоступен", 500);
  },

  async getLegalSources(documentId: string) {
    try {
      const payload = await request<LegalSourcesResponse>(
        `/documents/${documentId}/legal-sources`,
        { timeoutMs: 90000 }
      );
      return payload.legal_sources ?? [];
    } catch (error) {
      if (!isEndpointUnavailable(error)) {
        throw error;
      }
    }

    try {
      const report = await this.getDocumentReport(documentId);
      return report.legal_sources ?? [];
    } catch {
      return [] as LegalSource[];
    }
  },

  getDocuments() {
    return request<DocumentResponse[]>("/documents", { timeoutMs: 25000 });
  },

  getDocument(documentId: string) {
    return request<DocumentResponse>(`/documents/${documentId}`, { timeoutMs: 25000 });
  },

  register(payload: RegisterRequest) {
    return request<UserResponse>("/auth/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      timeoutMs: 30000
    });
  },

  login(payload: LoginRequest) {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      timeoutMs: 30000
    });
  },

  getMe() {
    return request<UserResponse>("/auth/me", { timeoutMs: 25000 });
  }
};

export function saveAuthToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function hasAuthToken(): boolean {
  return Boolean(localStorage.getItem(AUTH_TOKEN_KEY));
}

export { ApiError };
