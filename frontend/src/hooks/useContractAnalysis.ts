<<<<<<< HEAD
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiClient } from "../services/api";
import type { AnalyzeResponse, DocumentResponse, ProcessResponse, UploadResponse } from "../types/api";
=======
﻿import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, apiClient } from "../services/api";
import type {
  ContractReport,
  DocumentQuestionResponse,
  DocumentResponse,
  LegacyAnalyzeResponse,
  ProcessResponse,
  Risk,
  UploadResponse
} from "../types/api";
>>>>>>> feature/backend-mvp

type AsyncState = "idle" | "loading" | "success" | "error";

type PipelineError = {
<<<<<<< HEAD
  stage: "health" | "upload" | "process" | "analyze" | "documents";
=======
  stage: "health" | "upload" | "process" | "analyze" | "documents" | "question";
>>>>>>> feature/backend-mvp
  message: string;
} | null;

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
<<<<<<< HEAD
=======
const DEFAULT_DISCLAIMER =
  "Внешняя проверка выполняется по публично доступным источникам и не заменяет профессионального юриста.";
>>>>>>> feature/backend-mvp

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

<<<<<<< HEAD
=======
function normalizeRisk(risk: LegacyAnalyzeResponse["risks"][number]): Risk {
  return {
    title: risk.type,
    severity: risk.severity,
    explanation: risk.description,
    quote: risk.recommendation,
    page: null
  };
}

function resolveOverallRisk(risks: Risk[]): ContractReport["overall_risk"] {
  const severities = risks.map((risk) => risk.severity);
  if (severities.includes("critical")) return "critical";
  if (severities.includes("high")) return "high";
  if (severities.includes("medium")) return "medium";
  if (severities.includes("low")) return "low";
  return "unknown";
}

function normalizeReport(
  documentId: string,
  response: ContractReport | LegacyAnalyzeResponse
): ContractReport {
  if ("overall_risk" in response) {
    return {
      ...response,
      legal_sources: response.legal_sources ?? [],
      key_terms: response.key_terms ?? [],
      risks: response.risks ?? [],
      disclaimer: response.disclaimer || DEFAULT_DISCLAIMER
    };
  }

  const risks = (response.risks ?? []).map(normalizeRisk);
  return {
    document_id: documentId,
    status: response.status,
    summary: response.summary,
    overall_risk: resolveOverallRisk(risks),
    risks,
    key_terms: [],
    legal_sources: [],
    disclaimer: DEFAULT_DISCLAIMER
  };
}

>>>>>>> feature/backend-mvp
export function useContractAnalysis() {
  const [healthState, setHealthState] = useState<AsyncState>("idle");
  const [uploadState, setUploadState] = useState<AsyncState>("idle");
  const [processState, setProcessState] = useState<AsyncState>("idle");
  const [analyzeState, setAnalyzeState] = useState<AsyncState>("idle");
  const [documentsState, setDocumentsState] = useState<AsyncState>("idle");
<<<<<<< HEAD
=======
  const [questionState, setQuestionState] = useState<AsyncState>("idle");
>>>>>>> feature/backend-mvp

  const [error, setError] = useState<PipelineError>(null);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [processResult, setProcessResult] = useState<ProcessResponse | null>(null);
<<<<<<< HEAD
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);
  const [analysisInput, setAnalysisInput] = useState("");

=======
  const [report, setReport] = useState<ContractReport | null>(null);
  const [analysisInput, setAnalysisInput] = useState("");

  const [questionInput, setQuestionInput] = useState("");
  const [questionResult, setQuestionResult] = useState<DocumentQuestionResponse | null>(null);

>>>>>>> feature/backend-mvp
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
<<<<<<< HEAD
      setError({
        stage: "upload",
        message: "Поддерживаются только форматы PDF и DOCX."
      });
=======
      setError({ stage: "upload", message: "Поддерживаются только форматы PDF и DOCX." });
>>>>>>> feature/backend-mvp
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
<<<<<<< HEAD
      setError({
        stage: "upload",
        message: "Размер файла превышает 20 MB."
      });
=======
      setError({ stage: "upload", message: "Размер файла превышает 20 MB." });
>>>>>>> feature/backend-mvp
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
<<<<<<< HEAD
    setProcessResult(null);
    setAnalysisResult(null);
=======
    setQuestionState("idle");
    setProcessResult(null);
    setReport(null);
    setQuestionResult(null);
    setQuestionInput("");
>>>>>>> feature/backend-mvp
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
<<<<<<< HEAD
    setAnalysisResult(null);
=======
    setReport(null);
>>>>>>> feature/backend-mvp
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
<<<<<<< HEAD
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
=======

    setAnalyzeState("loading");
    setQuestionState("idle");
    setQuestionResult(null);
    setError(null);

    try {
      const analyzeResponse = await apiClient.analyzeDocument(uploadResult.document_id, {
        legacyText: analysisInput,
        preferOrchestrator: true
      });

      const normalizedReport = normalizeReport(uploadResult.document_id, analyzeResponse);

      if (!normalizedReport.legal_sources?.length) {
        const legalSources = await apiClient.getLegalSources(uploadResult.document_id);
        normalizedReport.legal_sources = legalSources;
      }

      setReport(normalizedReport);
>>>>>>> feature/backend-mvp
      setAnalyzeState("success");
      await loadDocuments();
    } catch (errorValue) {
      setAnalyzeState("error");
      setError({ stage: "analyze", message: parseError(errorValue) });
    }
  }, [analysisInput, loadDocuments, uploadResult]);

<<<<<<< HEAD
=======
  const askQuestion = useCallback(async () => {
    if (!uploadResult?.document_id) {
      setError({ stage: "question", message: "Сначала загрузите документ." });
      return;
    }
    if (!questionInput.trim()) {
      setError({ stage: "question", message: "Введите вопрос по документу." });
      return;
    }

    setQuestionState("loading");
    setError(null);

    try {
      const result = await apiClient.askDocumentQuestion(uploadResult.document_id, questionInput);
      setQuestionResult(result);
      setQuestionState("success");
    } catch (errorValue) {
      setQuestionState("error");
      setError({ stage: "question", message: parseError(errorValue) });
    }
  }, [questionInput, uploadResult?.document_id]);

>>>>>>> feature/backend-mvp
  const refreshSelectedDocument = useCallback(async () => {
    if (!uploadResult?.document_id) {
      return;
    }
    try {
<<<<<<< HEAD
      const fresh = await apiClient.getDocument(uploadResult.document_id);
=======
      const fresh = await apiClient.getDocumentStatus(uploadResult.document_id);
>>>>>>> feature/backend-mvp
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
<<<<<<< HEAD
    Boolean(analysisInput.trim()) &&
    processState === "success" &&
    analyzeState !== "loading";

  const isBusy = useMemo(
    () => [uploadState, processState, analyzeState].some((state) => state === "loading"),
    [analyzeState, processState, uploadState]
=======
    (processState === "success" || Boolean(analysisInput.trim())) &&
    analyzeState !== "loading";

  const isBusy = useMemo(
    () => [uploadState, processState, analyzeState, questionState].some((state) => state === "loading"),
    [analyzeState, processState, questionState, uploadState]
>>>>>>> feature/backend-mvp
  );

  return {
    healthState,
    uploadState,
    processState,
    analyzeState,
    documentsState,
<<<<<<< HEAD
=======
    questionState,
>>>>>>> feature/backend-mvp
    documents,
    selectedFile,
    uploadResult,
    processResult,
<<<<<<< HEAD
    analysisResult,
=======
    report,
>>>>>>> feature/backend-mvp
    analysisInput,
    error,
    isBusy,
    canProcess,
    canAnalyze,
<<<<<<< HEAD
    setAnalysisInput,
=======
    questionInput,
    questionResult,
    setAnalysisInput,
    setQuestionInput,
>>>>>>> feature/backend-mvp
    pickFile,
    uploadDocument,
    processDocument,
    analyzeDocument,
<<<<<<< HEAD
=======
    askQuestion,
>>>>>>> feature/backend-mvp
    checkHealth,
    loadDocuments,
    refreshSelectedDocument
  };
}
