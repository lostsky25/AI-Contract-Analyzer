import type { ContractReport, LegalSource, Risk } from "../types/api";

function normalize(value: string | null | undefined): string {
  return String(value ?? "").trim().toLowerCase();
}

const GENERIC_WARNING_FALLBACK = "Анализ завершился с предупреждением. Проверьте результат вручную.";

const MOJIBAKE_MARKERS = [
  "рџс",
  "р в°",
  "р вµ",
  "р р…",
  "р с‘",
  "рўрѓ",
  "рўвљ",
  "гђ",
  "г‘",
  "пїѕ",
  "пїЅ"
];

function looksLikeMojibake(value: string): boolean {
  const lowered = normalize(value);
  return MOJIBAKE_MARKERS.some((marker) => lowered.includes(marker));
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

export function getLegalSourceTypeLabel(sourceType: LegalSource["source_type"]): string {
  return formatSourceTypeLabel(sourceType);
}

export function formatRelevanceLabel(relevance: LegalSource["relevance"]): string {
  switch (relevance) {
    case "low":
      return "Низкая релевантность";
    case "medium":
      return "Средняя релевантность";
    case "high":
      return "Высокая релевантность";
    default:
      return "Релевантность не указана";
  }
}

export function formatConfidenceLabel(confidence: "low" | "medium" | "high" | "unknown"): string {
  switch (confidence) {
    case "low":
      return "Низкая уверенность";
    case "medium":
      return "Средняя уверенность";
    case "high":
      return "Высокая уверенность";
    default:
      return "Уверенность не указана";
  }
}

export function getRelevanceLabel(relevance: LegalSource["relevance"]): string {
  return formatRelevanceLabel(relevance);
}

export function getLegalSourceTrustLabel(trustTier: LegalSource["trust_tier"]): string {
  switch (trustTier) {
    case "grounded":
      return "Проверенный источник";
    case "model_reported":
      return "Требует ручной проверки";
    default:
      return "Требует проверки";
  }
}

export function getLegalSourceTrustTone(
  trustTier: LegalSource["trust_tier"]
): "good" | "warn" | "neutral" {
  switch (trustTier) {
    case "grounded":
      return "good";
    case "model_reported":
      return "warn";
    default:
      return "neutral";
  }
}

export function isInfoWarning(message: string): boolean {
  return normalize(message).startsWith("info:");
}

export function formatWarningLabel(message: string): string {
  const text = String(message ?? "").trim();
  if (!text) return "";
  const lowered = normalize(text);

  if (looksLikeMojibake(text)) {
    return GENERIC_WARNING_FALLBACK;
  }

  if (
    lowered.startsWith("provider_") ||
    lowered.startsWith("openrouter_") ||
    lowered.startsWith("bothub_") ||
    lowered.includes("providererror") ||
    lowered.includes("traceback")
  ) {
    return GENERIC_WARNING_FALLBACK;
  }

  if (
    lowered.includes("model-structured") ||
    lowered.includes("model_reported") ||
    lowered.includes("manual verification") ||
    lowered.includes("manual check") ||
    (lowered.includes("structured") && lowered.includes("model") && lowered.includes("source"))
  ) {
    return "Некоторые правовые источники получены из структурированного ответа модели и требуют ручной проверки.";
  }

  if (lowered.includes("local ocr fallback") || lowered.includes("ocr fallback")) {
    return "Часть текста была распознана через резервный OCR, возможны ошибки распознавания.";
  }

  if (
    lowered.includes("ground") &&
    (lowered.includes("rejected") || lowered.includes("discarded") || lowered.includes("dropped"))
  ) {
    return "Часть результатов была отброшена, потому что не подтверждалась цитатами из договора.";
  }

  if (lowered.includes("provider returned text links") || lowered.includes("plain-text url")) {
    return "Провайдер вернул ссылки без валидной структуры, поэтому они не показаны.";
  }

  if (lowered.includes("outside allowed domains")) {
    return "Проверка источников вернула ссылки вне разрешенных доменов.";
  }

  if (lowered.includes("invalid or placeholder") || lowered.includes("placeholder")) {
    return "Проверка источников вернула невалидные ссылки.";
  }

  const clean = text.replace(/^INFO:\s*/i, "").trim();
  if (looksLikeMojibake(clean)) {
    return GENERIC_WARNING_FALLBACK;
  }
  return clean || GENERIC_WARNING_FALLBACK;
}

export function formatSeverityLabel(severity: Risk["severity"]): string {
  switch (severity) {
    case "low":
      return "Низкий";
    case "medium":
      return "Средний";
    case "high":
      return "Высокий";
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
    default:
      return "Неизвестно";
  }
}
