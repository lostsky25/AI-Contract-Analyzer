import { useMemo, useState } from "react";

import type { ContractReport, DocumentQuestionResponse } from "../types/api";
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

export function ReportTabs({
  report,
  questionInput,
  questionState,
  questionResult,
  onQuestionChange,
  onAskQuestion
}: ReportTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const tabs = useMemo(
    () => [
      { id: "overview" as const, label: "Обзор" },
      { id: "risks" as const, label: `Риски (${report.risks.length})` },
      { id: "terms" as const, label: `Ключевые условия (${report.key_terms.length})` },
      { id: "sources" as const, label: `Источники (${report.legal_sources.length})` },
      { id: "questions" as const, label: "Вопросы" }
    ],
    [report.key_terms.length, report.legal_sources.length, report.risks.length]
  );

  return (
    <section className="report-tabs">
      <div className="report-tab-list">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`report-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
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

        {activeTab === "sources" ? <LegalSourcesPanel legalSources={report.legal_sources} /> : null}

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
