import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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

type AsyncState = "idle" | "loading" | "success" | "error";

type PipelineError = {
  stage: "health" | "upload" | "process" | "analyze" | "documents" | "question" | "report";
  message: string;
} | null;

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const DEFAULT_DISCLAIMER = "Система выполняет предварительный анализ и не заменяет профессионального юриста.";

const REPORT_READY_STATUSES = new Set(["done", "done_with_warnings", "analyzed"]);
const PROCESS_NEEDED_STATUSES = new Set(["uploaded", "failed_processing"]);
const BUSY_DOCUMENT_STATUSES = new Set(["processing", "analyzing"]);

function getFileExtension(fileName: string): string {
  const parts = fileName.toLowerCase().split(".");
  return parts.length > 1 ? `.${parts[parts.length - 1]}` : "";
}

function normalizeStatus(status: string | null | undefined): string {
  return String(status ?? "").trim().toLowerCase();
}

function parseError(error: unknown): string {
  const codeMessages: Record<string, string> = {
    provider_rate_limited:
      "Лимит AI-провайдера исчерпан. Попробуйте позже или смените модель.",
    openrouter_rate_limited:
      "Лимит AI-провайдера исчерпан. Попробуйте позже или смените модель.",
    provider_auth_failed: "AI-провайдер отклонил ключ доступа. Проверьте настройки API key.",
    openrouter_auth_failed: "AI-провайдер отклонил ключ доступа. Проверьте OPENROUTER_API_KEY.",
    provider_model_not_found: "Выбранная AI-модель недоступна. Проверьте настройки модели.",
    openrouter_model_not_found:
      "Выбранная AI-модель недоступна в OpenRouter. Проверьте настройки модели.",
    provider_missing_key: "AI-провайдер не настроен. Укажите API key в окружении backend.",
    openrouter_missing_key: "AI-провайдер не настроен. Укажите OPENROUTER_API_KEY в backend.",
    provider_unavailable: "AI-провайдер временно недоступен. Попробуйте позже.",
    openrouter_unavailable: "AI-провайдер временно недоступен. Попробуйте позже.",
    provider_bad_response: "AI-провайдер вернул неожиданный ответ. Попробуйте позже.",
    openrouter_bad_response: "AI-провайдер вернул неожиданный ответ. Попробуйте позже."
  };

  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return "Сессия истекла. Войдите снова.";
    }
    if (error.code === "openrouter_timeout" || error.code === "provider_timeout") {
      return "AI-анализ занимает больше обычного. Попробуйте ещё раз или проверьте статус документа позже.";
    }
    if (error.kind === "timeout") {
      return "Запрос к серверу выполняется дольше обычного. Попробуйте ещё раз.";
    }
    if (error.code && codeMessages[error.code]) {
      return codeMessages[error.code];
    }
    if (error.status === 500) {
      return "На сервере произошла ошибка. Проверьте логи backend.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка";
}

function normalizeRisk(risk: LegacyAnalyzeResponse["risks"][number]): Risk {
  const severity = risk.severity === "critical" ? "high" : risk.severity;
  return {
    title: risk.type,
    severity,
    explanation: risk.description,
    quote: risk.recommendation ?? "",
    page: null,
    chunk_id: null
  };
}

function resolveOverallRisk(risks: Risk[]): ContractReport["overall_risk"] {
  const severities = risks.map((risk) => risk.severity);
  if (severities.includes("high")) return "high";
  if (severities.includes("medium")) return "medium";
  if (severities.includes("low")) return "low";
  return "unknown";
}

function normalizeOrchestratorRisk(risk: Record<string, unknown>): Risk {
  const title = String(risk.title ?? risk.type ?? "Risk").trim() || "Risk";
  const explanation = String(risk.explanation ?? risk.description ?? "").trim();
  const severityRaw = String(risk.severity ?? "unknown").toLowerCase();
  const severity = (["low", "medium", "high", "unknown"] as const).includes(
    severityRaw as Risk["severity"]
  )
    ? (severityRaw as Risk["severity"])
    : "unknown";

  return {
    title,
    severity,
    explanation,
    quote: String(risk.quote ?? risk.recommendation ?? "").trim(),
    page: typeof risk.page === "number" ? risk.page : null,
    chunk_id: typeof risk.chunk_id === "string" ? risk.chunk_id : null
  };
}

function normalizeReport(documentId: string, response: ContractReport | LegacyAnalyzeResponse): ContractReport {
  if ("overall_risk" in response) {
    const risks = (response.risks ?? []).map((risk) => normalizeOrchestratorRisk(risk as Record<string, unknown>));
    return {
      ...response,
      legal_sources: response.legal_sources ?? [],
      key_terms: response.key_terms ?? [],
      risks,
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

function toUploadResult(document: DocumentResponse): UploadResponse {
  return {
    document_id: document.document_id,
    filename: document.filename,
    status: document.status
  };
}

function toDocumentResponse(upload: UploadResponse): DocumentResponse {
  return {
    document_id: upload.document_id,
    filename: upload.filename,
    status: upload.status,
    text_length: null,
    created_at: new Date().toISOString()
  };
}

export function useContractAnalysis() {
  const [healthState, setHealthState] = useState<AsyncState>("idle");
  const [uploadState, setUploadState] = useState<AsyncState>("idle");
  const [processState, setProcessState] = useState<AsyncState>("idle");
  const [analyzeState, setAnalyzeState] = useState<AsyncState>("idle");
  const [documentsState, setDocumentsState] = useState<AsyncState>("idle");
  const [questionState, setQuestionState] = useState<AsyncState>("idle");

  const [error, setError] = useState<PipelineError>(null);
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [processResult, setProcessResult] = useState<ProcessResponse | null>(null);
  const [report, setReport] = useState<ContractReport | null>(null);
  const [reportCache, setReportCache] = useState<Record<string, ContractReport>>({});
  const [openingReportDocumentId, setOpeningReportDocumentId] = useState<string | null>(null);
  const [analysisInput, setAnalysisInput] = useState("");
  const reportOpenRequestIdRef = useRef(0);

  const [questionInput, setQuestionInput] = useState("");
  const [questionResult, setQuestionResult] = useState<DocumentQuestionResponse | null>(null);
  const [legalWebSearchEnabled, setLegalWebSearchEnabled] = useState(true);

  const syncDocumentInList = useCallback((document: DocumentResponse) => {
    setDocuments((previous) => {
      const hasDoc = previous.some((item) => item.document_id === document.document_id);
      if (!hasDoc) {
        return [document, ...previous];
      }
      return previous.map((item) => (item.document_id === document.document_id ? document : item));
    });
  }, []);

  const resolveDocumentStatus = useCallback(async (document: DocumentResponse): Promise<DocumentResponse> => {
    try {
      return await apiClient.getDocumentStatus(document.document_id);
    } catch {
      return document;
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setDocumentsState("loading");
    try {
      const result = await apiClient.getDocuments();
      setDocuments(result);
      setSelectedDocument((prev) => {
        if (!prev) return prev;
        const next = result.find((doc) => doc.document_id === prev.document_id);
        if (next) {
          setUploadResult(toUploadResult(next));
          return next;
        }
        return prev;
      });
      setDocumentsState("success");
    } catch (errorValue) {
      setDocumentsState("error");
      setError({ stage: "documents", message: parseError(errorValue) });
    }
  }, []);

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
      setError({ stage: "upload", message: "Поддерживаются только форматы PDF и DOCX." });
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError({ stage: "upload", message: "Размер файла превышает 20 MB." });
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
    setQuestionState("idle");
    setProcessResult(null);
    setReport(null);
    setQuestionResult(null);
    setQuestionInput("");
    setAnalysisInput("");
    setError(null);

    try {
      const result = await apiClient.uploadDocument(selectedFile);
      const optimistic = toDocumentResponse(result);
      setUploadResult(result);
      setSelectedDocument(optimistic);
      setSelectedFile(null);
      syncDocumentInList(optimistic);
      setUploadState("success");
      await loadDocuments();
    } catch (errorValue) {
      setUploadState("error");
      setError({ stage: "upload", message: parseError(errorValue) });
    }
  }, [loadDocuments, selectedFile, syncDocumentInList]);

  const loadReportForDocument = useCallback(async (document: DocumentResponse): Promise<ContractReport | null> => {
    try {
      const loadedReport = await apiClient.fetchExistingReport(document.document_id);
      return normalizeReport(document.document_id, loadedReport);
    } catch {
      return null;
    }
  }, []);

  const selectDocument = useCallback(
    async (document: DocumentResponse) => {
      setError(null);
      setSelectedFile(null);
      setProcessResult(null);
      setQuestionInput("");
      setQuestionResult(null);
      setAnalysisInput("");
      setReport(null);
      setAnalyzeState("idle");
      setProcessState("idle");

      const freshDocument = await resolveDocumentStatus(document);
      setSelectedDocument(freshDocument);
      setUploadResult(toUploadResult(freshDocument));
      syncDocumentInList(freshDocument);

      const normalized = normalizeStatus(freshDocument.status);
      if (normalized === "processed" || normalized === "extracted" || normalized === "indexed") {
        setProcessState("success");
      }

      if (REPORT_READY_STATUSES.has(normalized)) {
        setAnalyzeState("loading");
        const loadedReport = await loadReportForDocument(freshDocument);
        if (loadedReport) {
          setReport(loadedReport);
          setReportCache((previous) => ({
            ...previous,
            [freshDocument.document_id]: loadedReport
          }));
          setAnalyzeState("success");
          setSelectedDocument((prev) =>
            prev
              ? {
                  ...prev,
                  status: loadedReport.status
                }
              : prev
          );
        } else {
          setAnalyzeState("idle");
          setError({ stage: "report", message: "Отчет для этого документа пока не сформирован." });
        }
      }
    },
    [loadReportForDocument, resolveDocumentStatus, syncDocumentInList]
  );

  const openReportForDocument = useCallback(
    async (document: DocumentResponse) => {
      const requestId = reportOpenRequestIdRef.current + 1;
      reportOpenRequestIdRef.current = requestId;

      setError(null);
      setSelectedFile(null);
      setProcessResult(null);
      setQuestionInput("");
      setQuestionResult(null);
      setAnalysisInput("");
      setProcessState("idle");
      setOpeningReportDocumentId(document.document_id);

      const cachedReport = reportCache[document.document_id];
      if (cachedReport) {
        setReport(cachedReport);
        setAnalyzeState("success");
      } else {
        setAnalyzeState("loading");
      }

      const freshDocument = await resolveDocumentStatus(document);
      if (requestId !== reportOpenRequestIdRef.current) {
        return;
      }
      setSelectedDocument(freshDocument);
      setUploadResult(toUploadResult(freshDocument));
      syncDocumentInList(freshDocument);

      try {
        const loadedReportRaw = await apiClient.fetchExistingReport(freshDocument.document_id);
        if (requestId !== reportOpenRequestIdRef.current) {
          return;
        }
        const loadedReport = normalizeReport(freshDocument.document_id, loadedReportRaw);
        setReport(loadedReport);
        setReportCache((previous) => ({
          ...previous,
          [freshDocument.document_id]: loadedReport
        }));
        setAnalyzeState("success");
        setSelectedDocument((prev) =>
          prev
            ? {
                ...prev,
                status: loadedReport.status
              }
            : prev
        );
      } catch (errorValue) {
        if (requestId !== reportOpenRequestIdRef.current) {
          return;
        }
        if (cachedReport) {
          setAnalyzeState("success");
          setError({
            stage: "report",
            message: "Не удалось обновить отчет с сервера. Показана последняя сохраненная версия."
          });
        } else {
          setAnalyzeState("error");
          setError({
            stage: "report",
            message: parseError(errorValue) || "Отчет для этого документа пока не сформирован."
          });
        }
      } finally {
        if (requestId === reportOpenRequestIdRef.current) {
          setOpeningReportDocumentId(null);
        }
      }
    },
    [reportCache, resolveDocumentStatus, syncDocumentInList]
  );

  const runAnalysisPipeline = useCallback(async () => {
    const activeDocument = selectedDocument ?? (uploadResult ? toDocumentResponse(uploadResult) : null);

    if (!activeDocument) {
      setError({ stage: "analyze", message: "Загрузите документ перед запуском анализа." });
      return;
    }

    setError(null);
    setQuestionState("idle");
    setQuestionResult(null);

    let current = await resolveDocumentStatus(activeDocument);
    const currentStatus = normalizeStatus(current.status);

    setSelectedDocument(current);
    setUploadResult(toUploadResult(current));
    syncDocumentInList(current);

    if (BUSY_DOCUMENT_STATUSES.has(currentStatus) || processState === "loading" || analyzeState === "loading") {
      return;
    }

    let legacyText = analysisInput;

    if (PROCESS_NEEDED_STATUSES.has(currentStatus) || (currentStatus === "failed" && !current.text_length)) {
      setProcessState("loading");
      try {
        const processed = await apiClient.processDocument({
          document_id: current.document_id
        });

        legacyText = processed.full_text || processed.text_preview || "";
        setProcessResult(processed);
        setAnalysisInput(legacyText);
        setProcessState("success");

        current = {
          ...current,
          status: processed.status,
          text_length: processed.text_length
        };
        setSelectedDocument(current);
        setUploadResult(toUploadResult(current));
        syncDocumentInList(current);
      } catch (errorValue) {
        setProcessState("error");
        const message = parseError(errorValue);
        const lower = message.toLowerCase();
        const isRecoverableFileError =
          errorValue instanceof ApiError && [400, 404].includes(errorValue.status ?? 0);
        const isFileUnavailable =
          lower.includes("file not found") ||
          lower.includes("document not found") ||
          lower.includes("not found");
        setError({
          stage: "process",
          message: isRecoverableFileError || isFileUnavailable
            ? "Не удалось обработать документ. Возможно, файл недоступен на сервере."
            : message
        });
        return;
      }
    } else if (["processed", "extracted", "indexed", "done", "done_with_warnings", "analyzed"].includes(currentStatus)) {
      setProcessState("success");
    } else {
      setProcessState("idle");
    }

    setAnalyzeState("loading");
    try {
      const analyzedResponse = await apiClient.analyzeDocument(current.document_id, {
        legacyText,
        preferOrchestrator: true,
        legalWebSearchEnabled
      });

      let normalizedReport = normalizeReport(current.document_id, analyzedResponse);

      if (legalWebSearchEnabled && !normalizedReport.legal_sources?.length) {
        const legalSources = await apiClient.getLegalSources(current.document_id);
        normalizedReport.legal_sources = legalSources;
      }

      const endpointReport = await loadReportForDocument(current);
      if (endpointReport) {
        normalizedReport = endpointReport;
      }

      setReport(normalizedReport);
      setReportCache((previous) => ({
        ...previous,
        [current.document_id]: normalizedReport
      }));
      setAnalyzeState("success");

      current = {
        ...current,
        status: normalizedReport.status
      };
      setSelectedDocument(current);
      setUploadResult(toUploadResult(current));
      syncDocumentInList(current);
      await loadDocuments();
    } catch (errorValue) {
      setAnalyzeState("error");
      setError({ stage: "analyze", message: parseError(errorValue) });
    }
  }, [
    analysisInput,
    analyzeState,
    legalWebSearchEnabled,
    loadDocuments,
    loadReportForDocument,
    processState,
    resolveDocumentStatus,
    selectedDocument,
    syncDocumentInList,
    uploadResult
  ]);

  const processDocument = useCallback(async () => {
    await runAnalysisPipeline();
  }, [runAnalysisPipeline]);

  const analyzeDocument = useCallback(async () => {
    await runAnalysisPipeline();
  }, [runAnalysisPipeline]);

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
      setQuestionResult({
        ...result,
        confidence: result.confidence ?? "unknown",
        citations: result.citations ?? [],
        disclaimer: result.disclaimer ?? DEFAULT_DISCLAIMER
      });
      setQuestionState("success");
    } catch (errorValue) {
      setQuestionState("error");
      setError({ stage: "question", message: parseError(errorValue) });
    }
  }, [questionInput, uploadResult?.document_id]);

  const refreshSelectedDocument = useCallback(async () => {
    const activeDocument = selectedDocument ?? (uploadResult ? toDocumentResponse(uploadResult) : null);
    if (!activeDocument) {
      return;
    }

    const fresh = await resolveDocumentStatus(activeDocument);
    setSelectedDocument(fresh);
    setUploadResult(toUploadResult(fresh));
    syncDocumentInList(fresh);
  }, [resolveDocumentStatus, selectedDocument, syncDocumentInList, uploadResult]);

  const selectedStatus = report?.status ?? selectedDocument?.status ?? uploadResult?.status ?? "";
  const normalizedSelectedStatus = normalizeStatus(selectedStatus);
  const hasSelectedDocument = Boolean(selectedDocument ?? uploadResult);
  const hasUnuploadedFile = Boolean(selectedFile);

  const canProcess = false;
  const canAnalyze =
    hasSelectedDocument &&
    !hasUnuploadedFile &&
    !BUSY_DOCUMENT_STATUSES.has(normalizedSelectedStatus) &&
    processState !== "loading" &&
    analyzeState !== "loading";

  const isBusy = useMemo(
    () => [uploadState, processState, analyzeState, questionState].some((state) => state === "loading"),
    [analyzeState, processState, questionState, uploadState]
  );

  return {
    healthState,
    uploadState,
    processState,
    analyzeState,
    documentsState,
    questionState,
    documents,
    selectedDocument,
    selectedFile,
    uploadResult,
    processResult,
    report,
    reportCache,
    openingReportDocumentId,
    analysisInput,
    error,
    isBusy,
    canProcess,
    canAnalyze,
    selectedStatus: normalizedSelectedStatus,
    hasSelectedDocument,
    hasUnuploadedFile,
    questionInput,
    questionResult,
    legalWebSearchEnabled,
    setLegalWebSearchEnabled,
    setAnalysisInput,
    setQuestionInput,
    pickFile,
    selectDocument,
    uploadDocument,
    processDocument,
    analyzeDocument,
    runAnalysisPipeline,
    openReportForDocument,
    askQuestion,
    checkHealth,
    loadDocuments,
    refreshSelectedDocument
  };
}


