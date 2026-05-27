import type {
  AnalyzeRequest,
  AnalyzeResponse,
  DocumentResponse,
  HealthResponse,
  ProcessRequest,
  ProcessResponse,
  UploadResponse
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
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
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as unknown;
      message = normalizeError(payload);
    } catch {
      // Ignore JSON parse errors and keep fallback message.
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
  analyzeDocument(payload: AnalyzeRequest) {
    return request<AnalyzeResponse>("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },
  getDocuments() {
    return request<DocumentResponse[]>("/documents");
  },
  getDocument(documentId: string) {
    return request<DocumentResponse>(`/documents/${documentId}`);
  }
};

export { ApiError };
