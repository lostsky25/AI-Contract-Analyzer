import { useMemo, useState } from "react";

import type { ContractReport, DocumentQuestionResponse } from "../types/api";
import { formatWarningLabel, isInfoWarning } from "../utils/labels";
import { KeyTermsList } from "./KeyTermsList";
import { LegalSourcesPanel } from "./LegalSourcesPanel";
import { OverallRiskBadge } from "./OverallRiskBadge";
import { QuestionsTab } from "./QuestionsTab";
import { RiskCard } from "./RiskCard";

type TabId = "overview" | "risks" | "terms" | "sources" | "questions";

type ReportTabsProps = {
  report: ContractReport;
  questionInput: string;
  questionState: "idle" | "loading" | "success" | "error";
  questionResult: DocumentQuestionResponse | null;
  onQuestionChange: (value: string) => void;
  onAskQuestion: () => void;
};

type ReportTab = {
  id: TabId;
  label: string;
  count?: number;
};

const MAX_VISIBLE_WARNINGS = 3;

function isLegalWarning(message: string): boolean {
  const normalized = message.toLowerCase();
  return ["legal", "source", "источник", "домен", "url", "web", "правов", "manual", "ссылк"].some((token) =>
    normalized.includes(token)
  );
}

function isSeriousGlobalWarning(message: string): boolean {
  const normalized = message.toLowerCase();
  return [
    "недостаточно извлеч",
    "недостаточно текста",
    "не удалось распознать",
    "резервный ocr",
    "упрощенном режиме",
    "часть данных отчета потребовала нормализации",
    "ошибка доступа к ai-провайдеру",
    "внешний ai-провайдер недоступен",
    "ai-провайдер не настроен",
    "лимит ai-провайдера",
    "выбранная ai-модель недоступна",
    "не ответил вовремя",
    "unexpected",
    "provider"
  ].some((token) => normalized.includes(token));
}

export function ReportTabs({
  report,
  questionInput,
  questionState,
  questionResult,
  onQuestionChange,
  onAskQuestion
}: ReportTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [showAllWarnings, setShowAllWarnings] = useState(false);

  const tabs = useMemo<ReportTab[]>(
    () => [
      { id: "overview" as const, label: "Обзор" },
      { id: "risks" as const, label: "Риски", count: report.risks.length },
      { id: "terms" as const, label: "Ключевые условия", count: report.key_terms.length },
      { id: "sources" as const, label: "Правовые источники", count: report.legal_sources.length },
      { id: "questions" as const, label: "Вопросы" }
    ],
    [report.key_terms.length, report.legal_sources.length, report.risks.length]
  );

  const warningMessages = useMemo(() => {
    const seen = new Set<string>();
    return (report.warnings ?? [])
      .filter((warning) => !isInfoWarning(warning))
      .map(formatWarningLabel)
      .filter((warning) => {
        if (!warning || seen.has(warning)) {
          return false;
        }
        seen.add(warning);
        return true;
      });
  }, [report.warnings]);

  const infoMessages = useMemo(() => {
    const seen = new Set<string>();
    return (report.warnings ?? [])
      .filter((warning) => isInfoWarning(warning))
      .map(formatWarningLabel)
      .filter((warning) => {
        if (!warning || seen.has(warning)) {
          return false;
        }
        seen.add(warning);
        return true;
      });
  }, [report.warnings]);

  const legalWarnings = useMemo(
    () => warningMessages.filter((warning) => isLegalWarning(warning)),
    [warningMessages]
  );

  const seriousGlobalWarnings = useMemo(
    () => warningMessages.filter((warning) => !isLegalWarning(warning) && isSeriousGlobalWarning(warning)),
    [warningMessages]
  );

  const softGlobalNotices = useMemo(
    () => warningMessages.filter((warning) => !isLegalWarning(warning) && !isSeriousGlobalWarning(warning)),
    [warningMessages]
  );

  const visibleSeriousWarnings = showAllWarnings
    ? seriousGlobalWarnings
    : seriousGlobalWarnings.slice(0, MAX_VISIBLE_WARNINGS);

  return (
    <section className="report-tabs">
      {seriousGlobalWarnings.length ? (
        <section className="report-warnings-panel" aria-live="polite">
          <p className="report-warnings-title">Анализ выполнен с предупреждениями</p>
          <ul className="report-warnings-list">
            {visibleSeriousWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          {seriousGlobalWarnings.length > MAX_VISIBLE_WARNINGS ? (
            <button
              type="button"
              className="button text report-warnings-toggle"
              onClick={() => setShowAllWarnings((current) => !current)}
            >
              {showAllWarnings ? "Свернуть" : "Показать ещё"}
            </button>
          ) : null}
        </section>
      ) : null}

      {!seriousGlobalWarnings.length && (softGlobalNotices.length || infoMessages.length) ? (
        <section className="report-notice-panel" aria-live="polite">
          <p className="report-notice-title">Примечания анализа</p>
          <ul className="report-notice-list">
            {softGlobalNotices.map((message) => (
              <li key={message}>{message}</li>
            ))}
            {infoMessages.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="report-tab-list">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`report-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.label}</span>
            {typeof tab.count === "number" ? <span className="report-tab-count">{tab.count}</span> : null}
          </button>
        ))}
      </div>

      <div className="report-tab-panel">
        {activeTab === "overview" ? (
          <div className="overview-block">
            <div className="overview-metrics">
              <div>
                <p className="muted">Общий риск</p>
                <OverallRiskBadge risk={report.overall_risk} />
              </div>
              <div>
                <p className="muted">Рисков</p>
                <strong>{report.risks.length}</strong>
              </div>
              <div>
                <p className="muted">Ключевых условий</p>
                <strong>{report.key_terms.length}</strong>
              </div>
              <div>
                <p className="muted">Правовых источников</p>
                <strong>{report.legal_sources.length}</strong>
              </div>
            </div>
            <p className="summary">{report.summary}</p>
            <p className="muted">{report.disclaimer}</p>
          </div>
        ) : null}

        {activeTab === "risks" ? (
          <div className="risk-list">
            {report.risks.length ? (
              report.risks.map((risk, index) => <RiskCard key={`${risk.title}-${index}`} risk={risk} />)
            ) : (
              <p className="muted">Риски не обнаружены.</p>
            )}
          </div>
        ) : null}

        {activeTab === "terms" ? <KeyTermsList terms={report.key_terms} /> : null}

        {activeTab === "sources" ? (
          <LegalSourcesPanel legalSources={report.legal_sources} legalWarnings={legalWarnings} />
        ) : null}

        {activeTab === "questions" ? (
          <QuestionsTab
            questionInput={questionInput}
            questionState={questionState}
            questionResult={questionResult}
            onQuestionChange={onQuestionChange}
            onAsk={onAskQuestion}
          />
        ) : null}
      </div>
    </section>
  );
}
