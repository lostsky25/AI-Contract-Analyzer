export type UploadResponse = {
  document_id: string;
  filename: string;
  status: string;
  file_path: string;
};

export type ProcessRequest = {
  document_id: string;
  file_path: string;
};

export type ProcessResponse = {
  document_id: string;
  status: string;
  text_preview: string;
  full_text: string;
  text_length: number;
  chunks_count: number;
  used_ocr: boolean;
};

export type AnalyzeRequest = {
  text: string;
  document_id?: string | null;
};

export type Risk = {
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  recommendation?: string;
};

export type AnalyzeResponse = {
  status: string;
  summary: string;
  risks: Risk[];
};

export type DocumentResponse = {
  document_id: string;
  filename: string;
  file_path: string;
  status: string;
  text_length: number | null;
  created_at: string;
};

export type HealthResponse = {
  status: string;
};
