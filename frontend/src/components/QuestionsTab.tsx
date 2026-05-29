import type { DocumentQuestionResponse } from "../types/api";
import { formatRelevanceLabel } from "../utils/labels";

type QuestionsTabProps = {
  questionInput: string;
  questionState: "idle" | "loading" | "success" | "error";
  questionResult: DocumentQuestionResponse | null;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
};

function confidenceLabel(value: string): string {
  if (value === "low" || value === "medium" || value === "high") {
    return formatRelevanceLabel(value);
  }
  return "Неизвестно";
}

export function QuestionsTab({
  questionInput,
  questionState,
  questionResult,
  onQuestionChange,
  onAsk
}: QuestionsTabProps) {
  const confidence = questionResult?.confidence ?? "unknown";
  const confidenceClass = `severity severity-${confidence}`;
  const citations = questionResult?.citations ?? [];

  return (
    <div className="questions-tab">
      <p className="muted">Задайте вопрос по тексту загруженного договора.</p>
      <div className="qa-form">
        <input
          type="text"
          value={questionInput}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Задайте вопрос по документу..."
        />
        <button className="button primary" type="button" onClick={onAsk} disabled={questionState === "loading"}>
          {questionState === "loading" ? "Идет поиск..." : "Задать вопрос"}
        </button>
      </div>

      {questionState === "error" && !questionResult ? (
        <p className="muted">Не удалось получить ответ. Попробуйте повторить запрос позже.</p>
      ) : null}

      {questionResult ? (
        <article className="qa-answer">
          <p>
            <strong>Ответ:</strong> {questionResult.answer}
          </p>
          <p>
            <strong>Уверенность:</strong> <span className={confidenceClass}>{confidenceLabel(confidence)}</span>
          </p>
          <div>
            <strong>Цитаты:</strong>
            {citations.length ? (
              <ul>
                {citations.map((citation, index) => (
                  <li key={`${citation.chunk_id}-${index}`}>
                    {citation.quote}
                    {typeof citation.page === "number" ? ` (стр. ${citation.page})` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">Цитаты не найдены.</p>
            )}
          </div>
          <p className="muted">{questionResult.disclaimer}</p>
        </article>
      ) : null}
    </div>
  );
}
