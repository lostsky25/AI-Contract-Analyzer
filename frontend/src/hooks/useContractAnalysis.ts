import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiClient } from "../services/api";
import type { AnalyzeResponse, DocumentResponse, ProcessResponse, UploadResponse } from "../types/api";

type AsyncState = "idle" | "loading" | "success" | "error";

type PipelineError = {
  stage: "health" | "upload" | "process" | "analyze" | "documents";
  message: string;
} | null;

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

function getFileExtension(fileName: string): string {
  const parts = fileName.toLowerCase().split(".");
  return parts.length > 1 ? `.${parts[parts.length - 1]}` : "";
}

function parseError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка";
}

export function useContractAnalysis() {
  const [healthState, setHealthState] = useState<AsyncState>("idle");
  const [uploadState, setUploadState] = useState<AsyncState>("idle");
  const [processState, setProcessState] = useState<AsyncState>("idle");
  const [analyzeState, setAnalyzeState] = useState<AsyncState>("idle");
  const [documentsState, setDocumentsState] = useState<AsyncState>("idle");

  const [error, setError] = useState<PipelineError>(null);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [processResult, setProcessResult] = useState<ProcessResponse | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);
  const [analysisInput, setAnalysisInput] = useState("");

  const checkHealth = useCallback(async () => {
    setHealthState("loading");
    setError(null);
    try {
      await apiClient.getHealth();
      setHealthState("success");
    } catch (errorValue) {
      setHealthState("error");
      setError({ stage: "health", message: parseError(errorValue) });
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setDocumentsState("loading");
    try {
      const result = await apiClient.getDocuments();
      setDocuments(result);
      setDocumentsState("success");
    } catch (errorValue) {
      setDocumentsState("error");
      setError({ stage: "documents", message: parseError(errorValue) });
    }
  }, []);

  useEffect(() => {
    void checkHealth();
    void loadDocuments();
  }, [checkHealth, loadDocuments]);

  const pickFile = useCallback((file: File | null) => {
    setError(null);
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const extension = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setSelectedFile(null);
      setError({
        stage: "upload",
        message: "Поддерживаются только форматы PDF и DOCX."
      });
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError({
        stage: "upload",
        message: "Размер файла превышает 20 MB."
      });
      return;
    }

    setSelectedFile(file);
  }, []);

  const uploadDocument = useCallback(async () => {
    if (!selectedFile) {
      setError({ stage: "upload", message: "Сначала выберите файл." });
      return;
    }

    setUploadState("loading");
    setProcessState("idle");
    setAnalyzeState("idle");
    setProcessResult(null);
    setAnalysisResult(null);
    setAnalysisInput("");
    setError(null);

    try {
      const result = await apiClient.uploadDocument(selectedFile);
      setUploadResult(result);
      setUploadState("success");
      await loadDocuments();
    } catch (errorValue) {
      setUploadState("error");
      setError({ stage: "upload", message: parseError(errorValue) });
    }
  }, [loadDocuments, selectedFile]);

  const processDocument = useCallback(async () => {
    if (!uploadResult) {
      setError({ stage: "process", message: "Сначала загрузите документ." });
      return;
    }

    setProcessState("loading");
    setAnalyzeState("idle");
    setAnalysisResult(null);
    setError(null);

    try {
      const result = await apiClient.processDocument({
        document_id: uploadResult.document_id,
        file_path: uploadResult.file_path
      });
      setProcessResult(result);
      setAnalysisInput(result.full_text ?? result.text_preview ?? "");
      setProcessState("success");
      await loadDocuments();
    } catch (errorValue) {
      setProcessState("error");
      setError({ stage: "process", message: parseError(errorValue) });
    }
  }, [loadDocuments, uploadResult]);

  const analyzeDocument = useCallback(async () => {
    if (!uploadResult) {
      setError({ stage: "analyze", message: "Нет document_id. Выполните upload." });
      return;
    }
    if (!analysisInput.trim()) {
      setError({ stage: "analyze", message: "Нет текста для анализа." });
      return;
    }

    setAnalyzeState("loading");
    setError(null);

    try {
      const result = await apiClient.analyzeDocument({
        text: analysisInput,
        document_id: uploadResult.document_id
      });
      setAnalysisResult(result);
      setAnalyzeState("success");
      await loadDocuments();
    } catch (errorValue) {
      setAnalyzeState("error");
      setError({ stage: "analyze", message: parseError(errorValue) });
    }
  }, [analysisInput, loadDocuments, uploadResult]);

  const refreshSelectedDocument = useCallback(async () => {
    if (!uploadResult?.document_id) {
      return;
    }
    try {
      const fresh = await apiClient.getDocument(uploadResult.document_id);
      setDocuments((previous) => {
        const hasDoc = previous.some((doc) => doc.document_id === fresh.document_id);
        if (!hasDoc) {
          return [fresh, ...previous];
        }
        return previous.map((doc) => (doc.document_id === fresh.document_id ? fresh : doc));
      });
    } catch {
      // Non-blocking refresh.
    }
  }, [uploadResult?.document_id]);

  const canProcess = Boolean(uploadResult) && processState !== "loading";
  const canAnalyze =
    Boolean(uploadResult) &&
    Boolean(analysisInput.trim()) &&
    processState === "success" &&
    analyzeState !== "loading";

  const isBusy = useMemo(
    () => [uploadState, processState, analyzeState].some((state) => state === "loading"),
    [analyzeState, processState, uploadState]
  );

  return {
    healthState,
    uploadState,
    processState,
    analyzeState,
    documentsState,
    documents,
    selectedFile,
    uploadResult,
    processResult,
    analysisResult,
    analysisInput,
    error,
    isBusy,
    canProcess,
    canAnalyze,
    setAnalysisInput,
    pickFile,
    uploadDocument,
    processDocument,
    analyzeDocument,
    checkHealth,
    loadDocuments,
    refreshSelectedDocument
  };
}
