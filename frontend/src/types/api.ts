export type UploadResponse = {
  document_id: string;
  filename: string;
  status: string;
};

export type ProcessRequest = {
  document_id: string;
};

export type ProcessResponse = {
  document_id: string;
  status: string;
  text_preview: string;
  full_text: string;
  text_length: number;
  chunks_count: number;
  used_ocr: boolean;
  warnings?: string[];
};

export type AnalyzeRequest = {
  text: string;
  document_id?: string | null;
};

export type DocumentAnalyzeRequest = {
  legal_web_search_enabled?: boolean;
};

export type OrchestrateRequest = {
  document_id: string;
  legal_web_search_enabled?: boolean;
};

export type Risk = {
  title: string;
  severity: "low" | "medium" | "high" | "unknown";
  explanation: string;
  quote: string;
  page?: number | null;
  chunk_id?: string | null;
};

export type KeyTerm = {
  title: string;
  value: string;
  explanation?: string;
  quote: string;
  page?: number | null;
  chunk_id?: string | null;
};

export type LegalSource = {
  title: string;
  url: string;
  snippet: string;
  reason?: string;
  source_type: "consultant_plus" | "garant" | "pravo_gov" | "other_public_source";
  relevance: "low" | "medium" | "high" | "unknown";
  trust_tier?: "grounded" | "model_reported";
};

export type ContractReport = {
  document_id: string;
  status: string;
  summary: string;
  overall_risk: "low" | "medium" | "high" | "unknown";
  risks: Risk[];
  key_terms: KeyTerm[];
  legal_sources: LegalSource[];
  warnings?: string[];
  disclaimer: string;
  used_ocr?: boolean;
  chunks_count?: number;
};

export type LegacyAnalyzeRisk = {
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  recommendation?: string;
};

export type LegacyAnalyzeResponse = {
  status: string;
  summary: string;
  risks: LegacyAnalyzeRisk[];
};

export type DocumentResponse = {
  document_id: string;
  filename: string;
  status: string;
  text_length: number | null;
  created_at: string;
};

export type DocumentStatusResponse = {
  document_id: string;
  status: string;
};

export type HealthResponse = {
  status: string;
};

export type DocumentQuestionCitation = {
  quote: string;
  page?: number | null;
  chunk_id: string;
};

export type DocumentQuestionResponse = {
  document_id: string;
  question: string;
  answer: string;
  confidence: "low" | "medium" | "high" | "unknown";
  citations: DocumentQuestionCitation[];
  disclaimer: string;
  status?: string;
  model?: string;
  fallback_model?: string;
};

export type LegalSourcesResponse = {
  document_id: string;
  legal_sources: LegalSource[];
  warnings: string[];
};

export type RegisterRequest = {
  username: string;
  email: string;
  password: string;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type UserResponse = {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: UserResponse;
};
