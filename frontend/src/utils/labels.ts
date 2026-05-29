import type { ContractReport, LegalSource, Risk } from "../types/api";

function normalize(value: string | null | undefined): string {
  return String(value ?? "").trim().toLowerCase();
}

export function formatStatusLabel(status: string | null | undefined): string {
  switch (normalize(status)) {
    case "uploaded":
      return "Загружен";
    case "processed":
    case "extracted":
    case "indexed":
      return "Обработан";
    case "processing":
      return "В обработке";
    case "analyzing":
      return "Анализируется";
    case "done":
    case "analyzed":
      return "Готово";
    case "done_with_warnings":
      return "С предупреждениями";
    case "failed":
    case "failed_processing":
      return "Ошибка";
    default:
      return "Неизвестно";
  }
}

export function formatSourceTypeLabel(sourceType: LegalSource["source_type"]): string {
  switch (sourceType) {
    case "consultant_plus":
      return "КонсультантПлюс";
    case "garant":
      return "Гарант";
    case "pravo_gov":
      return "pravo.gov.ru";
    default:
      return "Публичный источник";
  }
}

export function formatRelevanceLabel(relevance: LegalSource["relevance"]): string {
  switch (relevance) {
    case "low":
      return "Низкая";
    case "medium":
      return "Средняя";
    case "high":
      return "Высокая";
    default:
      return "Неизвестно";
  }
}

export function formatSeverityLabel(severity: Risk["severity"]): string {
  switch (severity) {
    case "low":
      return "Низкий";
    case "medium":
      return "Средний";
    case "high":
      return "Высокий";
    case "critical":
      return "Критичный";
    default:
      return "Неизвестно";
  }
}

export function formatOverallRiskLabel(risk: ContractReport["overall_risk"]): string {
  switch (risk) {
    case "low":
      return "Низкий";
    case "medium":
      return "Средний";
    case "high":
      return "Высокий";
    case "critical":
      return "Критичный";
    default:
      return "Неизвестно";
  }
}
