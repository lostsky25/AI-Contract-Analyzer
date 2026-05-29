import { DocumentsTable } from "../components/DocumentsTable";
import { DisclaimerBlock } from "../components/DisclaimerBlock";
import { OverallRiskBadge } from "../components/OverallRiskBadge";
import { ReportTabs } from "../components/ReportTabs";
import { StatusBadge } from "../components/StatusBadge";
import { StepCard } from "../components/StepCard";
import { useContractAnalysis } from "../hooks/useContractAnalysis";
import { AppShell } from "../layouts/AppShell";

type DashboardPageProps = {
  currentUsername: string;
  onLogout: () => void;
};

export function DashboardPage({ currentUsername, onLogout }: DashboardPageProps) {
  const model = useContractAnalysis();

  return (
    <AppShell
      backendHealthy={model.healthState === "success"}
      userLabel={currentUsername}
      onLogout={onLogout}
    >
      <section className="hero reveal">
        <h2>Загрузка, обработка и AI-анализ договоров</h2>
        <p>
          Основной сценарий: <strong>upload → process → analyze</strong>. Обработка может занять до
          30-60 секунд. Во время выполнения отображаются loading и статусы этапов.
        </p>
      </section>

      {model.error ? (
        <section className="alert reveal">
          <strong>Ошибка на этапе {model.error.stage}:</strong> {model.error.message}
        </section>
      ) : null}

      <section className="grid-3">
        <StepCard
          title="1. Upload"
          description="Поддерживаются PDF и DOCX до 20 MB."
          actionLabel="Загрузить документ"
          onAction={() => void model.uploadDocument()}
          loading={model.uploadState === "loading"}
          disabled={!model.selectedFile || model.isBusy}
          done={model.uploadState === "success"}
        >
          <label className="file-input">
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(event) => model.pickFile(event.target.files?.[0] ?? null)}
            />
            <span>{model.selectedFile ? model.selectedFile.name : "Выбрать файл"}</span>
          </label>
          {model.uploadResult ? (
            <p className="meta">
              Document ID: <code>{model.uploadResult.document_id}</code>
            </p>
          ) : null}
        </StepCard>

        <StepCard
          title="2. Process"
          description="Извлечение текста, OCR (при необходимости), chunking и индексация."
          actionLabel="Запустить обработку"
          onAction={() => void model.processDocument()}
          loading={model.processState === "loading"}
          disabled={!model.canProcess || model.isBusy}
          done={model.processState === "success"}
        >
          {model.processResult ? (
            <div className="meta">
              <StatusBadge value={model.processResult.status} /> · chunks: <strong>{model.processResult.chunks_count}</strong> · OCR:{" "}
              <strong>{model.processResult.used_ocr ? "да" : "нет"}</strong>
            </div>
          ) : (
            <p className="muted">После успешного upload появятся данные обработки.</p>
          )}
        </StepCard>

        <StepCard
          title="3. Analyze"
          description="Сборка структурированного отчета: summary, risks, key terms, legal sources, Q&A."
          actionLabel="Запустить AI-анализ"
          onAction={() => void model.analyzeDocument()}
          loading={model.analyzeState === "loading"}
          disabled={!model.canAnalyze || model.isBusy}
          done={model.analyzeState === "success"}
        >
          <p className="meta">Этап анализа может быть долгим при первом запуске и больших документах.</p>
        </StepCard>
      </section>

      <section className="grid-2">
        <article className="card reveal">
          <div className="section-head">
            <h3>Текст для fallback-анализа</h3>
            <button className="button ghost" onClick={() => void model.refreshSelectedDocument()} type="button">
              Обновить статус документа
            </button>
          </div>
          <textarea
            className="text-area"
            value={model.analysisInput}
            onChange={(event) => model.setAnalysisInput(event.target.value)}
            placeholder="После process здесь появится текст документа."
          />
        </article>

        <article className="card reveal">
          <div className="section-head">
            <h3>Структурированный отчёт</h3>
            {model.report ? <OverallRiskBadge risk={model.report.overall_risk} /> : null}
          </div>

          {!model.report ? (
            <p className="muted">Запустите анализ, чтобы увидеть summary, риски, ключевые условия и источники.</p>
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
        </article>
      </section>

      <DocumentsTable
        documents={model.documents}
        onRefresh={() => void model.loadDocuments()}
        loading={model.documentsState === "loading"}
      />
    </AppShell>
  );
}
