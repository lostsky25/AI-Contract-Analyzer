import type { DocumentQuestionResponse } from "../types/api";

type QuestionsTabProps = {
  questionInput: string;
  questionState: "idle" | "loading" | "success" | "error";
  questionResult: DocumentQuestionResponse | null;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
};

export function QuestionsTab({
  questionInput,
  questionState,
  questionResult,
  onQuestionChange,
  onAsk
}: QuestionsTabProps) {
  return (
    <div className="questions-tab">
      <p className="muted">
        Вкладка вопросов подготовлена под agent-based Q&A и citations. Если endpoint ещё не
        подключен, можно оставить этот блок как placeholder.
      </p>
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

      {questionResult ? (
        <article className="qa-answer">
          <p>
            <strong>Ответ:</strong> {questionResult.answer}
          </p>
          <p className="muted">Уверенность: {questionResult.confidence}</p>
          <p className="muted">{questionResult.disclaimer}</p>
        </article>
      ) : null}
    </div>
  );
}
