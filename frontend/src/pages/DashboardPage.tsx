import { useMemo, useRef } from "react";

import { DocumentsTable } from "../components/DocumentsTable";
import { DisclaimerBlock } from "../components/DisclaimerBlock";
import { OverallRiskBadge } from "../components/OverallRiskBadge";
import { ReportTabs } from "../components/ReportTabs";
import { StatusBadge } from "../components/StatusBadge";
import { useContractAnalysis } from "../hooks/useContractAnalysis";
import { AppShell } from "../layouts/AppShell";
import { formatDateTime } from "../utils/format";

type DashboardPageProps = {
  currentUsername: string;
  onLogout: () => void;
};

type StepState = "pending" | "active" | "done" | "failed";
type StepId = "upload" | "process" | "analyze" | "sources" | "report";

function fileTypeLabel(fileName: string | undefined): string {
  if (!fileName) return "N/A";
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".pdf")) return "PDF";
  if (lower.endsWith(".docx")) return "DOCX";
  return "FILE";
}

function normalizeErrorMessage(stage: string, message: string): string {
  if (stage === "analyze") {
    return `AI-анализ временно недоступен: ${message}`;
  }
  if (stage === "health") {
    return "Сервер временно недоступен. Проверьте соединение и повторите позже.";
  }
  if (stage === "question") {
    return "Вопросы по документу временно недоступны. Попробуйте позже.";
  }
  return message;
}

export function DashboardPage({ currentUsername, onLogout }: DashboardPageProps) {
  const model = useContractAnalysis();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fileName = model.uploadResult?.filename ?? model.selectedFile?.name;
  const fileType = fileTypeLabel(fileName);

  const quotes = useMemo(() => {
    if (!model.report) return [];
    const fromRisks = model.report.risks.map((risk) => ({
      quote: risk.quote ?? "",
      page: risk.page ?? null
    }));
    const fromTerms = model.report.key_terms.map((term) => ({
      quote: term.quote ?? "",
      page: term.page ?? null
    }));
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
        return "analyze";
      default:
        return null;
    }
  }, [model.error]);

  const steps = useMemo<Array<{ id: StepId; label: string; state: StepState }>>(() => {
    const hasUpload = Boolean(model.uploadResult);
    const hasProcess = Boolean(model.processResult);
    const hasAnalyze = Boolean(model.report);
    const sourcesReady = Boolean(
      model.report && ((model.report.legal_sources?.length ?? 0) > 0 || (model.report.warnings?.length ?? 0) > 0)
    );

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
        if (hasAnalyze) return "done";
        if (model.analyzeState === "loading") return "active";
      }
      return "pending";
    };

    return [
      { id: "upload", label: "Загрузка", state: resolve("upload") },
      { id: "process", label: "Обработка", state: resolve("process") },
      { id: "analyze", label: "Анализ", state: resolve("analyze") },
      { id: "sources", label: "Правовые источники", state: resolve("sources") },
      { id: "report", label: "Отчет", state: resolve("report") }
    ];
  }, [
    failedStep,
    model.analyzeState,
    model.processResult,
    model.processState,
    model.report,
    model.uploadResult,
    model.uploadState
  ]);

  const recentDocuments = useMemo(() => model.documents.slice(0, 5), [model.documents]);

  return (
    <AppShell backendHealthy={model.healthState === "success"} userLabel={currentUsername} onLogout={onLogout}>
      <div className="dashboard-grid">
        <section className="dashboard-main">
          <section className="hero-card reveal">
            <div className="hero-text">
              <h1>Проверяйте договоры быстрее и увереннее с помощью AI</h1>
              <p>
                Загрузите договор — система найдет риски, ключевые условия, цитаты, страницы и
                публичные правовые источники.
              </p>
            </div>
          </section>

          {model.healthState === "error" ? (
            <section className="inline-alert warning">
              Сервер недоступен. Dashboard продолжает работать, но запросы к API временно невозможны.
            </section>
          ) : null}

          {model.error ? (
            <section className="inline-alert danger">
              {normalizeErrorMessage(model.error.stage, model.error.message)}
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
                <button
                  className="button ghost"
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Выбрать файл
                </button>
              </div>
              <p className="meta">
                {model.selectedFile
                  ? `Выбран файл: ${model.selectedFile.name}`
                  : "Файл еще не выбран"}
              </p>
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
                <p className="muted">
                  {fileType} · ID: {model.uploadResult?.document_id ?? "—"}
                </p>
              </div>
              <div className="document-actions">
                <button
                  className="button ghost"
                  type="button"
                  onClick={() => void model.processDocument()}
                  disabled={!model.canProcess || model.processState === "loading"}
                >
                  {model.processState === "loading" ? "Обработка..." : "Запустить обработку"}
                </button>
                <button
                  className="button primary"
                  type="button"
                  onClick={() => void model.analyzeDocument()}
                  disabled={!model.canAnalyze || model.analyzeState === "loading"}
                >
                  {model.analyzeState === "loading" ? "Идет анализ..." : "Запустить анализ"}
                </button>
                <button
                  className="button ghost"
                  type="button"
                  onClick={() =>
                    document.getElementById("report-card")?.scrollIntoView({ behavior: "smooth", block: "start" })
                  }
                  disabled={!model.report}
                >
                  Открыть отчет
                </button>
                <button className="button ghost" type="button" disabled>
                  Экспорт PDF — позже
                </button>
              </div>
            </div>

            <div className="doc-meta-grid">
              <div className="doc-meta-item">
                <p className="muted">Статус</p>
                <StatusBadge value={model.report?.status ?? model.processResult?.status ?? "idle"} />
              </div>
              <div className="doc-meta-item">
                <p className="muted">Chunks</p>
                <strong>{model.processResult?.chunks_count ?? model.report?.chunks_count ?? 0}</strong>
              </div>
              <div className="doc-meta-item">
                <p className="muted">OCR</p>
                <strong>{model.processResult?.used_ocr ?? model.report?.used_ocr ? "да" : "нет"}</strong>
              </div>
              <div className="doc-meta-item">
                <p className="muted">Поиск источников</p>
                <label className="checkbox-option">
                  <input
                    type="checkbox"
                    checked={model.legalWebSearchEnabled}
                    onChange={(event) => model.setLegalWebSearchEnabled(event.target.checked)}
                    disabled={model.isBusy}
                  />
                  <span>{model.legalWebSearchEnabled ? "Включен" : "Отключен"}</span>
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

          <section className="card report-card reveal" id="report-card">
            {!model.report ? (
              <p className="muted">
                Запустите анализ, чтобы получить структурированный отчет по рискам, ключевым условиям,
                цитатам и правовым источникам.
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

          <DocumentsTable
            documents={model.documents}
            onRefresh={() => void model.loadDocuments()}
            loading={model.documentsState === "loading"}
          />
        </section>

        <aside className="dashboard-right">
          <section className="card side-card">
            <h3>Недавняя активность</h3>
            {!recentDocuments.length ? (
              <p className="muted">История пока пуста.</p>
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
              <li>Запустите обработку и анализ документа.</li>
              <li>Получите отчет с рисками, цитатами и источниками.</li>
            </ol>
            <p className="muted">Полнота проверки по законодательству не гарантируется.</p>
          </section>

          <section className="card side-card">
            <h3>Правовые источники</h3>
            {model.report?.legal_sources.length ? (
              <ul className="sources-mini-list">
                {model.report.legal_sources.slice(0, 3).map((source, index) => (
                  <li key={`${source.url}-${index}`}>
                    <strong>{source.title}</strong>
                    <p className="muted">{source.source_type}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                Правовые источники ищутся среди публично доступных материалов.
              </p>
            )}
          </section>

          <section className="card side-card">
            <p className="muted">
              Система выполняет предварительный анализ и не заменяет профессионального юриста.
            </p>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}
