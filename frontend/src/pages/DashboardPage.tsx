import { useEffect, useMemo, useRef, useState } from "react";

import { DisclaimerBlock } from "../components/DisclaimerBlock";
import { DocumentsTable } from "../components/DocumentsTable";
import { OverallRiskBadge } from "../components/OverallRiskBadge";
import { ReportTabs } from "../components/ReportTabs";
import { ReportsTable } from "../components/ReportsTable";
import { StatusBadge, statusLabel } from "../components/StatusBadge";
import { useContractAnalysis } from "../hooks/useContractAnalysis";
import { AppShell } from "../layouts/AppShell";
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
  const lower = message.toLowerCase();
  const providerUnavailable =
    lower.includes("openrouter") ||
    lower.includes("provider is unavailable") ||
    lower.includes("api key") ||
    lower.includes("request failed");

  if ((stage === "analyze" || stage === "report") && providerUnavailable) {
    return "AI-анализ временно недоступен. Проверьте настройку внешнего AI-провайдера.";
  }
  if (stage === "analyze") {
    return `AI-анализ временно недоступен: ${message}`;
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
    if (activeSection !== "documents" && searchQuery) {
      setSearchQuery("");
    }
  }, [activeSection, searchQuery]);

  const fileName = model.selectedDocument?.filename ?? model.uploadResult?.filename ?? model.selectedFile?.name;
  const fileType = fileTypeLabel(fileName);
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

  const steps = useMemo<Array<{ id: StepId; label: string; state: StepState }>>(() => {
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

    return [
      { id: "upload", label: "Загрузка", state: resolve("upload") },
      { id: "process", label: "Обработка", state: resolve("process") },
      { id: "analyze", label: "Анализ", state: resolve("analyze") },
      { id: "sources", label: "Источники", state: resolve("sources") },
      { id: "report", label: "Отчет", state: resolve("report") }
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
                    Загрузите договор и получите понятный отчет по рискам, ключевым условиям и рекомендациям за
                    несколько минут.
                  </p>
                </div>
                <div className="hero-visual" aria-hidden>
                  <div className="hero-glow" />
                  <div className="hero-shield">✓</div>
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
                <div className="dropzone-icon">⇪</div>
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
                  <p className="meta">{model.selectedFile ? `Выбран файл: ${model.selectedFile.name}` : "Файл еще не выбран"}</p>
                </div>
              </section>

              <section className="card stepper-card reveal">
                <div className="stepper-row">
                  {steps.map((step, index) => (
                    <div className={`step-item ${step.state}`} key={step.id}>
                      <span className="step-index">{index + 1}</span>
                      <span className="step-label">{step.label}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="card document-card reveal">
                <div className="document-head">
                  <div>
                    <h3>{fileName ?? "Документ пока не загружен"}</h3>
                    <p className="muted">{pipelineInfo}</p>
                  </div>
                  <div className="document-actions">
                    <button
                      className="button primary"
                      type="button"
                      onClick={() => void model.runAnalysisPipeline()}
                      disabled={analyzeAction.disabled}
                      title={analyzeAction.title}
                    >
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
                    <label className="checkbox-option">
                      <input
                        type="checkbox"
                        checked={model.legalWebSearchEnabled}
                        onChange={(event) => model.setLegalWebSearchEnabled(event.target.checked)}
                        disabled={model.isBusy}
                      />
                      <span>{model.legalWebSearchEnabled ? "Включена" : "Отключена"}</span>
                    </label>
                  </div>
                </div>
              </section>

              <section className="card summary-card reveal">
                <div className="summary-risk">
                  <p className="muted">Общий уровень риска</p>
                  {model.report ? <OverallRiskBadge risk={model.report.overall_risk} /> : <span className="muted">N/A</span>}
                  <p className="muted">Готовность: {completion}</p>
                </div>
                <div className="summary-metrics">
                  <div>
                    <p className="muted">Риски</p>
                    <strong>{model.report?.risks.length ?? 0}</strong>
                  </div>
                  <div>
                    <p className="muted">Ключевые условия</p>
                    <strong>{model.report?.key_terms.length ?? 0}</strong>
                  </div>
                  <div>
                    <p className="muted">Цитаты / страницы</p>
                    <strong>
                      {quotes.length} / {uniquePagesCount}
                    </strong>
                  </div>
                  <div>
                    <p className="muted">Правовые источники</p>
                    <strong>{model.report?.legal_sources.length ?? 0}</strong>
                  </div>
                </div>
              </section>

              <section className="card report-card reveal" id="report-card" ref={reportSectionRef}>
                {!model.report ? (
                  <p className="muted">
                    Запустите анализ, чтобы получить структурированный отчет по рискам, ключевым условиям, цитатам и
                    правовым источникам.
                  </p>
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
                    <div>
                      <strong>{doc.filename}</strong>
                      <p className="muted">{formatDateTime(doc.created_at)}</p>
                    </div>
                    <StatusBadge value={doc.status} />
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="card side-card">
            <h3>Как это работает?</h3>
            <ol className="how-list">
              <li>Загрузите договор в формате PDF или DOCX.</li>
              <li>Нажмите «Запустить анализ», система выполнит обработку и анализ.</li>
              <li>Получите структурированный отчет с пояснениями и цитатами.</li>
            </ol>
            <p className="muted">
              Правовые выводы требуют дополнительной проверки юристом в контексте вашей ситуации.
            </p>
          </section>

          <section className="card side-card">
            <p className="muted">Система выполняет предварительный анализ и не заменяет профессионального юриста.</p>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}
