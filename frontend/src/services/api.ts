import type {
  AnalyzeRequest,
  AuthResponse,
  ContractReport,
  DocumentQuestionResponse,
  DocumentResponse,
  HealthResponse,
  LegacyAnalyzeResponse,
  LegalSource,
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

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const headers = new Headers(init?.headers ?? {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers
  });

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
    return request<HealthResponse>("/health");
  },

  uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<UploadResponse>("/upload", {
      method: "POST",
      body: formData
    });
  },

  processDocument(payload: ProcessRequest) {
    return request<ProcessResponse>("/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  analyzeText(payload: AnalyzeRequest) {
    return request<LegacyAnalyzeResponse>("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  async analyzeDocument(
    documentId: string,
    options?: { legacyText?: string; preferOrchestrator?: boolean }
  ) {
    const variants: Array<() => Promise<ContractReport | LegacyAnalyzeResponse>> = [];

    if (options?.preferOrchestrator) {
      variants.push(() =>
        request<ContractReport>("/orchestrate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ document_id: documentId })
        })
      );
    }

    variants.push(
      () =>
        request<ContractReport>(`/documents/${documentId}/analyze`, {
          method: "POST"
        }),
      () =>
        request<ContractReport>(`/analyze/${documentId}`, {
          method: "POST"
        }),
      () =>
        request<ContractReport>("/orchestrate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ document_id: documentId })
        }),
      () =>
        request<LegacyAnalyzeResponse>("/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ document_id: documentId })
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
          })
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
      return await request<DocumentResponse>(`/documents/${documentId}/status`);
    } catch (error) {
      if (isEndpointUnavailable(error)) {
        return request<DocumentResponse>(`/documents/${documentId}`);
      }
      throw error;
    }
  },

  async getDocumentReport(documentId: string) {
    const variants: Array<() => Promise<ContractReport>> = [
      () => request<ContractReport>(`/documents/${documentId}/report`),
      () => request<ContractReport>(`/report/${documentId}`),
      () =>
        request<ContractReport>("/orchestrate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ document_id: documentId })
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

    throw lastError ?? new ApiError("Отчет по документу недоступен", 500);
  },

  async askDocumentQuestion(documentId: string, question: string) {
    const body = JSON.stringify({ question });
    const withDocument = JSON.stringify({ document_id: documentId, question });

    const variants: Array<() => Promise<DocumentQuestionResponse>> = [
      () =>
        request<DocumentQuestionResponse>(`/documents/${documentId}/questions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body
        }),
      () =>
        request<DocumentQuestionResponse>(`/documents/${documentId}/qa`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body
        }),
      () =>
        request<DocumentQuestionResponse>("/qa", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: withDocument
        }),
      () =>
        request<DocumentQuestionResponse>("/questions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: withDocument
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
    const variants: Array<() => Promise<LegalSource[]>> = [
      () => request<LegalSource[]>(`/documents/${documentId}/legal-sources`),
      () => request<LegalSource[]>(`/legal-sources/${documentId}`)
    ];

    for (const run of variants) {
      try {
        return await run();
      } catch (error) {
        if (!isEndpointUnavailable(error)) {
          throw error;
        }
      }
    }

    try {
      const report = await this.getDocumentReport(documentId);
      return report.legal_sources ?? [];
    } catch {
      return [];
    }
  },

  getDocuments() {
    return request<DocumentResponse[]>("/documents");
  },

  getDocument(documentId: string) {
    return request<DocumentResponse>(`/documents/${documentId}`);
  },

  register(payload: RegisterRequest) {
    return request<UserResponse>("/auth/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  login(payload: LoginRequest) {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  getMe() {
    return request<UserResponse>("/auth/me");
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
