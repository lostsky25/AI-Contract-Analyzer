import { useEffect, useMemo, useRef, useState } from "react";

import { DisclaimerBlock } from "../components/DisclaimerBlock";
import { DocumentsTable } from "../components/DocumentsTable";
import { OverallRiskBadge } from "../components/OverallRiskBadge";
import { ReportTabs } from "../components/ReportTabs";
import { ReportsTable } from "../components/ReportsTable";
import { StatusBadge, statusLabel } from "../components/StatusBadge";
import { useContractAnalysis } from "../hooks/useContractAnalysis";
import { AppShell } from "../layouts/AppShell";
import { AUTH_EXPIRED_EVENT } from "../services/api";
import type { DocumentResponse } from "../types/api";
import { formatDateTime } from "../utils/format";

type DashboardPageProps = {
  currentUsername: string;
  onLogout: () => void;
};

type StepState = "pending" | "active" | "done" | "failed";
type StepId = "upload" | "process" | "analyze" | "sources" | "report";
type SectionId = "home" | "documents" | "reports";

type AnalyzeActionState = {
  label: string;
  disabled: boolean;
  title?: string;
};

function fileTypeLabel(fileName: string | undefined): string {
  if (!fileName) return "N/A";
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".pdf")) return "PDF";
  if (lower.endsWith(".docx")) return "DOCX";
  return "FILE";
}

function normalizeStatus(status: string): string {
  return status.trim().toLowerCase();
}

function normalizeErrorMessage(stage: string, message: string): string {
  if (stage === "analyze") {
    return message || "AI-анализ временно недоступен.";
  }
  if (stage === "report") {
    return message || "Отчет для этого документа пока не сформирован.";
  }
  if (stage === "health") {
    return "Сервер временно недоступен. Проверьте соединение и повторите позже.";
  }
  if (stage === "question") {
    return "Вопросы по документу временно недоступны. Попробуйте позже.";
  }
  return message;
}

function matchesSearch(doc: DocumentResponse, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  const haystack = `${doc.filename} ${doc.status} ${doc.created_at}`.toLowerCase();
  return haystack.includes(normalized);
}

function resolveAnalyzeActionState(args: {
  status: string;
  hasSelectedDocument: boolean;
  hasUnuploadedFile: boolean;
  processState: string;
  analyzeState: string;
  hasReport: boolean;
}): AnalyzeActionState {
  const normalizedStatus = normalizeStatus(args.status);

  if (args.processState === "loading" || args.analyzeState === "loading") {
    return { label: "Анализ выполняется...", disabled: true };
  }

  if (normalizedStatus === "processing" || normalizedStatus === "analyzing") {
    return { label: "Анализ выполняется...", disabled: true };
  }

  if (!args.hasSelectedDocument || args.hasUnuploadedFile) {
    return {
      label: "Загрузите документ",
      disabled: true,
      title: "Сначала загрузите документ"
    };
  }

  if (normalizedStatus === "done_with_warnings") {
    return {
      label: args.hasReport ? "Повторить анализ" : "Запустить анализ",
      disabled: false
    };
  }

  if (normalizedStatus === "done" || normalizedStatus === "analyzed") {
    return {
      label: args.hasReport ? "Повторить анализ" : "Запустить анализ",
      disabled: false
    };
  }

  if (normalizedStatus === "failed" || normalizedStatus === "failed_processing") {
    return { label: "Повторить анализ", disabled: false };
  }

  return { label: "Запустить анализ", disabled: false };
}

export function DashboardPage({ currentUsername, onLogout }: DashboardPageProps) {
  const model = useContractAnalysis();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const reportSectionRef = useRef<HTMLElement | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSection, setActiveSection] = useState<SectionId>("home");

  useEffect(() => {
    const handleAuthExpired = () => onLogout();
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, [onLogout]);

  useEffect(() => {
    if (activeSection !== "documents" && searchQuery) {
      setSearchQuery("");
    }
  }, [activeSection, searchQuery]);

  const fileName = model.selectedDocument?.filename ?? model.uploadResult?.filename ?? model.selectedFile?.name;
  const fileType = fileTypeLabel(fileName);
  const documentFileClass = fileType === "PDF" ? "pdf" : fileType === "DOCX" ? "docx" : "file";
  const documentFileLabel = fileType === "PDF" ? "PDF" : fileType === "DOCX" ? "DOCX" : "FILE";
  const selectedStatus = model.selectedStatus || "unknown";
  const normalizedSelectedStatus = normalizeStatus(selectedStatus);
  const pipelineInfo = `${fileType} · ${statusLabel(selectedStatus)}`;

  const filteredDocuments = useMemo(
    () => model.documents.filter((doc) => matchesSearch(doc, searchQuery)),
    [model.documents, searchQuery]
  );
  const recentDocuments = useMemo(() => filteredDocuments.slice(0, 5), [filteredDocuments]);

  const quotes = useMemo(() => {
    if (!model.report) return [];
    const fromRisks = model.report.risks.map((risk) => ({ quote: risk.quote ?? "", page: risk.page ?? null }));
    const fromTerms = model.report.key_terms.map((term) => ({ quote: term.quote ?? "", page: term.page ?? null }));
    return [...fromRisks, ...fromTerms].filter((item) => item.quote.trim());
  }, [model.report]);

  const uniquePagesCount = useMemo(() => {
    const pages = new Set<number>();
    for (const item of quotes) {
      if (typeof item.page === "number") {
        pages.add(item.page);
      }
    }
    return pages.size;
  }, [quotes]);

  const completion = useMemo(() => {
    if (model.report) return "Готово";
    if (model.analyzeState === "loading") return "Выполняется анализ";
    if (model.processState === "loading") return "В обработке";
    if (model.uploadResult) return "Файл загружен";
    return "Ожидание";
  }, [model.analyzeState, model.processState, model.report, model.uploadResult]);

  const failedStep = useMemo<StepId | null>(() => {
    if (!model.error) return null;
    switch (model.error.stage) {
      case "upload":
        return "upload";
      case "process":
        return "process";
      case "analyze":
      case "report":
        return "analyze";
      default:
        return null;
    }
  }, [model.error]);

  const steps = useMemo<Array<{ id: StepId; label: string; state: StepState; warning?: boolean }>>(() => {
    const hasUpload = Boolean(model.hasSelectedDocument || model.uploadResult);
    const hasProcess =
      Boolean(model.processResult) ||
      ["processed", "extracted", "indexed", "done", "done_with_warnings", "analyzed"].includes(normalizedSelectedStatus);
    const hasAnalyze = Boolean(model.report) || ["done", "done_with_warnings", "analyzed"].includes(normalizedSelectedStatus);
    const sourcesReady = Boolean(
      (model.report && ((model.report.legal_sources?.length ?? 0) > 0 || (model.report.warnings?.length ?? 0) > 0)) ||
        normalizedSelectedStatus === "done_with_warnings"
    );
    const reportReady = Boolean(model.report);

    const resolve = (id: StepId): StepState => {
      if (failedStep === id) return "failed";
      if (id === "upload") {
        if (hasUpload) return "done";
        if (model.uploadState === "loading") return "active";
        return "pending";
      }
      if (id === "process") {
        if (hasProcess) return "done";
        if (model.processState === "loading") return "active";
        return "pending";
      }
      if (id === "analyze") {
        if (hasAnalyze) return "done";
        if (model.analyzeState === "loading") return "active";
        return "pending";
      }
      if (id === "sources") {
        if (sourcesReady) return "done";
        if (model.analyzeState === "loading") return "active";
        return "pending";
      }
      if (id === "report") {
        if (reportReady) return "done";
        if (model.analyzeState === "loading") return "active";
      }
      return "pending";
    };

    const warningDoneState = normalizedSelectedStatus === "done_with_warnings";

    return [
      { id: "upload", label: "Загрузка", state: resolve("upload") },
      { id: "process", label: "Обработка", state: resolve("process") },
      { id: "analyze", label: "Анализ", state: resolve("analyze"), warning: warningDoneState },
      { id: "sources", label: "Источники", state: resolve("sources"), warning: warningDoneState },
      { id: "report", label: "Отчёт", state: resolve("report"), warning: warningDoneState }
    ];
  }, [
    failedStep,
    model.analyzeState,
    model.hasSelectedDocument,
    model.processResult,
    model.processState,
    model.report,
    model.uploadResult,
    model.uploadState,
    normalizedSelectedStatus
  ]);

  const reportHasWarnings = model.report?.status === "done_with_warnings";
  const legalWarnings = model.report?.warnings ?? [];
  const hasLegalUnavailableWarning = legalWarnings.some((warning) => warning.toLowerCase().includes("unavailable"));

  const showHome = activeSection === "home";
  const showDocuments = activeSection === "documents";
  const showReports = activeSection === "reports";

  const analyzeAction = resolveAnalyzeActionState({
    status: selectedStatus,
    hasSelectedDocument: model.hasSelectedDocument,
    hasUnuploadedFile: model.hasUnuploadedFile,
    processState: model.processState,
    analyzeState: model.analyzeState,
    hasReport: Boolean(model.report)
  });
  const showAnalyzeCtaIcon = analyzeAction.label !== "Анализ выполняется...";

  return (
    <AppShell
      backendHealthy={model.healthState === "success"}
      userLabel={currentUsername}
      onLogout={onLogout}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      searchEnabled={activeSection === "documents"}
      activeSection={activeSection}
      onNavigate={(target) => {
        if (target === "home" || target === "documents" || target === "reports") {
          setActiveSection(target);
        }
      }}
    >
      <div className="dashboard-grid">
        <section className="dashboard-main">
          {showHome ? (
            <>
              <section className="hero-card reveal">
                <div className="hero-text">
                  <h1>Проверяйте договоры быстрее и увереннее с помощью AI</h1>
                  <p>
                    Загрузите договор и получите понятный отчёт по рискам, ключевым условиям и рекомендациям за
                    несколько минут.
                  </p>
                </div>
                <div className="hero-visual" aria-hidden>
                  <div className="hero-orbit" />
                  <div className="hero-orbit hero-orbit-small" />
                  <div className="hero-dot hero-dot-a" />
                  <div className="hero-dot hero-dot-b" />
                  <div className="hero-document">
                    <span />
                    <span />
                    <span />
                    <span />
                  </div>
                  <div className="hero-shield">
                    <div className="hero-check">✓</div>
                  </div>
                  <div className="hero-glow" />
                </div>
              </section>

              {model.healthState === "error" ? (
                <section className="inline-alert warning">
                  Сервер недоступен. Интерфейс работает, но запросы к API временно невозможны.
                </section>
              ) : null}

              {model.error ? (
                <section className="inline-alert danger">{normalizeErrorMessage(model.error.stage, model.error.message)}</section>
              ) : null}

              {reportHasWarnings ? (
                <section className="inline-alert info">
                  Анализ выполнен с предупреждениями.
                  {hasLegalUnavailableWarning
                    ? " Правовые источники могли быть частично недоступны."
                    : ""}
                </section>
              ) : null}

              <section className="card dropzone-card reveal">
                <input
                  ref={fileInputRef}
                  className="hidden-file-input"
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={(event) => model.pickFile(event.target.files?.[0] ?? null)}
                />
                <div className="dropzone-icon" aria-hidden>
                  <svg viewBox="0 0 24 24">
                    <path
                      d="M7.4 18.3A4.9 4.9 0 1 1 8.9 8.7a6 6 0 0 1 11.3 2.6A3.8 3.8 0 0 1 19 18.7h-3.8m-3.2 0v-8m0 0l-2.8 2.9m2.8-2.9l2.8 2.9"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="dropzone-content">
                  <h3>Перетащите файл договора сюда</h3>
                  <p className="muted">PDF и DOCX, до 20 MB</p>
                  <div className="dropzone-actions">
                    <button
                      className="button primary"
                      type="button"
                      onClick={() => void model.uploadDocument()}
                      disabled={!model.selectedFile || model.uploadState === "loading"}
                    >
                      {model.uploadState === "loading" ? "Загрузка..." : "Загрузить договор"}
                    </button>
                    <button className="button ghost" type="button" onClick={() => fileInputRef.current?.click()}>
                      Выбрать файл
                    </button>
                  </div>
                  <p className="meta dropzone-file-meta">
                    <span className="dropzone-file-icon" aria-hidden>
                      {model.selectedFile ? "L" : "i"}
                    </span>
                    <span>{model.selectedFile ? `Выбран файл: ${model.selectedFile.name}` : "Файл ещё не выбран"}</span>
                  </p>
                </div>
              </section>

              <section className="card stepper-card reveal">
                <div className="stepper-row">
                  {steps.map((step, index) => {
                    const nextStep = steps[index + 1];
                    const connectorClass = !nextStep
                      ? "connector-none"
                      : step.state === "done" && nextStep.state === "done"
                        ? "connector-done"
                        : step.state === "done" && nextStep.state === "active"
                          ? "connector-active"
                          : "connector-pending";

                    return (
                    <div
                      className={`step-item ${step.state} ${step.warning ? "warning" : ""} ${connectorClass}`}
                      key={step.id}
                    >
                      <span className="step-index">{step.state === "done" ? "✓" : index + 1}</span>
                      <span className="step-label">{step.label}</span>
                    </div>
                  );})}
                </div>
              </section>

              <section className="card document-card reveal">
                <div className="document-head">
                  <div className="document-identity">
                    <div className={`document-file-icon ${documentFileClass}`} aria-hidden>
                      <span className="document-file-corner" />
                      <span className="document-file-glyph">{documentFileLabel === "DOCX" ? "W" : documentFileLabel}</span>
                    </div>
                    <div>
                      <h3>{fileName ?? "Документ пока не загружен"}</h3>
                      <p className="muted document-pipeline">{pipelineInfo}</p>
                    </div>
                  </div>
                  <div className="document-actions">
                    <button
                      className="button primary analysis-cta"
                      type="button"
                      onClick={() => void model.runAnalysisPipeline()}
                      disabled={analyzeAction.disabled}
                      title={analyzeAction.title}
                    >
                      {showAnalyzeCtaIcon ? (
                        <span className="analysis-cta-icon" aria-hidden>
                          ▶
                        </span>
                      ) : null}
                      {analyzeAction.label}
                    </button>
                  </div>
                </div>

                <div className="doc-meta-grid">
                  <div className="doc-meta-item">
                    <p className="muted">Статус</p>
                    <StatusBadge value={selectedStatus} />
                  </div>
                  <div className="doc-meta-item">
                    <p className="muted">Web-проверка источников</p>
                    <label className="checkbox-option checkbox-option-card">
                      <input
                        type="checkbox"
                        checked={model.legalWebSearchEnabled}
                        onChange={(event) => model.setLegalWebSearchEnabled(event.target.checked)}
                        disabled={model.isBusy}
                      />
                      <span>
                        {model.legalWebSearchEnabled
                          ? "Web-проверка источников включена"
                          : "Web-проверка источников отключена"}
                      </span>
                    </label>
                  </div>
                </div>
              </section>

              <section className="card summary-card reveal">
                <div className="summary-risk">
                  <div className="summary-risk-head">
                    <span className="summary-metric-icon risk" aria-hidden>
                      <svg viewBox="0 0 24 24" role="presentation">
                        <path d="M12 2 19 5v6.1c0 5.1-3.2 9.5-7 10.9-3.8-1.4-7-5.8-7-10.9V5L12 2Z" />
                        <path d="M12 7.1v6.2M12 16.8h.01" />
                      </svg>
                    </span>
                    <p className="muted">Общий уровень риска</p>
                  </div>
                  {model.report ? <OverallRiskBadge risk={model.report.overall_risk} /> : <span className="muted">N/A</span>}
                  <p className="muted summary-risk-status">Готовность: {completion}</p>
                </div>
                <div className="summary-metrics">
                  <div className="summary-metric-card">
                    <span className="summary-metric-icon metric-risks" aria-hidden>
                      <svg viewBox="0 0 24 24" role="presentation">
                        <path d="M12 3 3 20h18L12 3Z" />
                        <path d="M12 9v5M12 17.2h.01" />
                      </svg>
                    </span>
                    <p className="muted">Риски</p>
                    <strong>{model.report?.risks.length ?? 0}</strong>
                  </div>
                  <div className="summary-metric-card">
                    <span className="summary-metric-icon metric-terms" aria-hidden>
                      <svg viewBox="0 0 24 24" role="presentation">
                        <path d="M6 4h12a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" />
                        <path d="M8.5 9h7M8.5 12h7M8.5 15h4.8" />
                      </svg>
                    </span>
                    <p className="muted">Ключевые условия</p>
                    <strong>{model.report?.key_terms.length ?? 0}</strong>
                  </div>
                  <div className="summary-metric-card">
                    <span className="summary-metric-icon metric-quotes" aria-hidden>
                      <svg viewBox="0 0 24 24" role="presentation">
                        <path d="M7.7 9.3A3.7 3.7 0 0 0 4 13v3.6c0 1.4 1.1 2.5 2.5 2.5h2.4c1.3 0 2.4-1.1 2.4-2.4v-2.6c0-1.2-1-2.2-2.2-2.2h-1c.3-1 .9-1.8 1.8-2.6.3-.2.3-.7 0-1L9 7.4a.8.8 0 0 0-1.3.1Zm8.6 0A3.7 3.7 0 0 0 12.6 13v3.6c0 1.4 1.1 2.5 2.5 2.5h2.4c1.3 0 2.4-1.1 2.4-2.4v-2.6c0-1.2-1-2.2-2.2-2.2h-1c.3-1 .9-1.8 1.8-2.6.3-.2.3-.7 0-1L17.7 7.4a.8.8 0 0 0-1.4.1Z" />
                      </svg>
                    </span>
                    <p className="muted">Цитаты / страницы</p>
                    <strong>
                      {quotes.length} / {uniquePagesCount}
                    </strong>
                  </div>
                  <div className="summary-metric-card">
                    <span className="summary-metric-icon metric-sources" aria-hidden>
                      <svg viewBox="0 0 24 24" role="presentation">
                        <path d="M12 3.2c4.8 0 8.8 3.9 8.8 8.8s-3.9 8.8-8.8 8.8S3.2 16.9 3.2 12s3.9-8.8 8.8-8.8Z" />
                        <path d="M12 6.8v10.4M8.2 9.1 12 7.8l3.8 1.3M7.6 10.3h2.6c1 0 1.8.8 1.8 1.8v1.2c0 1-.8 1.8-1.8 1.8H7.6m8.8-4.8H19c1 0 1.8.8 1.8 1.8v1.2c0 1-.8 1.8-1.8 1.8h-2.6" />
                      </svg>
                    </span>
                    <p className="muted">Правовые источники</p>
                    <strong>{model.report?.legal_sources.length ?? 0}</strong>
                  </div>
                </div>
              </section>

              <section className="card report-card reveal" id="report-card" ref={reportSectionRef}>
                {!model.report ? (
                  <div className="report-empty-state">
                    <p className="muted report-empty-text">
                      Запустите анализ, чтобы получить структурированный отчёт по рискам, ключевым условиям, цитатам и
                      правовым источникам.
                    </p>
                    {model.analyzeState === "loading" ? (
                      <p className="muted report-loading-text">Анализ выполняется. Отчёт появится сразу после завершения.</p>
                    ) : null}
                  </div>
                ) : (
                  <>
                    <ReportTabs
                      report={model.report}
                      questionInput={model.questionInput}
                      questionState={model.questionState}
                      questionResult={model.questionResult}
                      onQuestionChange={model.setQuestionInput}
                      onAskQuestion={() => void model.askQuestion()}
                    />
                    <DisclaimerBlock text={model.report.disclaimer} />
                  </>
                )}
              </section>
            </>
          ) : null}

          {showDocuments ? (
            <section className="section-panel">
              <DocumentsTable
                documents={filteredDocuments}
                onRefresh={() => void model.loadDocuments()}
                loading={model.documentsState === "loading"}
                searchQuery={searchQuery}
                selectedDocumentId={model.selectedDocument?.document_id ?? null}
                onSelect={(doc) => {
                  void model.selectDocument(doc).finally(() => {
                    setActiveSection("home");
                  });
                }}
              />
            </section>
          ) : null}

          {showReports ? (
            <section className="section-panel">
              <ReportsTable
                documents={model.documents}
                loading={model.documentsState === "loading"}
                selectedDocumentId={model.selectedDocument?.document_id ?? null}
                openingReportDocumentId={model.openingReportDocumentId}
                currentReport={model.report}
                reportCache={model.reportCache}
                onRefresh={() => void model.loadDocuments()}
                onOpenReport={(doc) => {
                  void model.openReportForDocument(doc).finally(() => {
                    setActiveSection("home");
                    setTimeout(() => {
                      reportSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                    }, 100);
                  });
                }}
              />
            </section>
          ) : null}
        </section>

        <aside className="dashboard-right">
          <section className="card side-card">
            <h3>Недавняя активность</h3>
            {!recentDocuments.length ? (
              <p className="muted">
                {searchQuery ? "По запросу ничего не найдено." : "История документов пока пуста."}
              </p>
            ) : (
              <div className="activity-list">
                {recentDocuments.map((doc) => (
                  <article key={doc.document_id} className="activity-item">
                    <div className={`activity-file-icon ${fileTypeLabel(doc.filename).toLowerCase()}`} aria-hidden>
                      {fileTypeLabel(doc.filename) === "PDF" ? "PDF" : "W"}
                    </div>
                    <div className="activity-item-main">
                      <strong>{doc.filename}</strong>
                      <p className="muted">{formatDateTime(doc.created_at)}</p>
                    </div>
                    <div className="activity-item-meta">
                      <StatusBadge value={doc.status} />
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="card side-card">
            <h3>Как это работает?</h3>
            <ol className="how-list">
              <li>
                <span className="how-step-number">1</span>
                <span>Загрузите договор в формате PDF или DOCX.</span>
              </li>
              <li>
                <span className="how-step-number">2</span>
                <span>Нажмите «Запустить анализ», система выполнит обработку и анализ.</span>
              </li>
              <li>
                <span className="how-step-number">3</span>
                <span>Получите структурированный отчёт с пояснениями и цитатами.</span>
              </li>
            </ol>
            <p className="muted">
              Правовые выводы требуют дополнительной проверки юристом в контексте вашей ситуации.
            </p>
          </section>

          <section className="card side-card">
            <h3 className="disclaimer-title">
              <span className="disclaimer-icon" aria-hidden>
                i
              </span>
              Дисклеймер
            </h3>
            <p className="muted">Система выполняет предварительный анализ и не заменяет профессионального юриста.</p>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}
