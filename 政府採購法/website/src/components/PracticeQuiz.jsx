import { useState } from "react";
import { Link } from "react-router-dom";
import QuestionView from "./QuestionView";
import { addWrongQuestion, removeWrongQuestion } from "../data/storage";

export default function PracticeQuiz({ questions, title, backTo = "/", backLabel = "← 回首頁" }) {
  const [index, setIndex] = useState(0);
  const [results, setResults] = useState({});

  if (questions.length === 0) {
    return (
      <div>
        <Link to={backTo} className="back-link">
          {backLabel}
        </Link>
        <p>目前沒有題目。</p>
      </div>
    );
  }

  const question = questions[index];
  const isLast = index === questions.length - 1;
  const finished = isLast && question.id in results;
  const answeredCount = Object.keys(results).length;
  const correctCount = Object.values(results).filter(Boolean).length;

  function handleAnswered(isCorrect) {
    if (isCorrect) removeWrongQuestion(question.id);
    else addWrongQuestion(question.id);
    setResults((prev) => ({ ...prev, [question.id]: isCorrect }));
  }

  function restart() {
    setIndex(0);
    setResults({});
  }

  return (
    <div>
      <div className="quiz-header">
        <Link to={backTo} className="back-link">
          {backLabel}
        </Link>
        <h2>{title}</h2>
        <p className="progress">
          第 {index + 1} / {questions.length} 題
          {answeredCount > 0 ? `（已作答 ${answeredCount} 題，答對 ${correctCount} 題）` : ""}
        </p>
      </div>

      <QuestionView key={question.id} question={question} onAnswered={handleAnswered} />

      {finished && (
        <div className="finish-banner">
          <p className="finish-title">本輪練習完成！</p>
          <p className="finish-score">
            {answeredCount === questions.length
              ? `共 ${questions.length} 題，答對 ${correctCount} 題（${Math.round((correctCount / questions.length) * 100)}%）`
              : `已作答 ${answeredCount} / ${questions.length} 題，答對 ${correctCount} 題（${Math.round((correctCount / answeredCount) * 100)}%，以已作答題數計算）`}
          </p>
          <div className="finish-actions">
            <button type="button" className="primary-btn" onClick={restart}>
              重新開始這一輪
            </button>
            <Link to={backTo}>{backLabel}</Link>
          </div>
        </div>
      )}

      <div className="quiz-nav">
        <button
          type="button"
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
        >
          上一題
        </button>
        <button
          type="button"
          onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}
          disabled={index === questions.length - 1}
        >
          下一題
        </button>
      </div>
    </div>
  );
}
