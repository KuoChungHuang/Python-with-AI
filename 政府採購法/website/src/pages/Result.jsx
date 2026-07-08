import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { addWrongQuestion, removeWrongQuestion } from "../data/storage";

const TF_LABELS = { true: "正確 (O)", false: "錯誤 (X)" };

export default function Result() {
  const location = useLocation();
  const state = location.state;

  const questions = state?.questions ?? [];
  const answers = state?.answers ?? {};

  const rows = questions.map((q) => {
    const answerKey = q.type === "tf" ? String(q.answer) : q.answer;
    const userAnswer = answers[q.id];
    const isCorrect = userAnswer === answerKey;
    return { q, userAnswer, isCorrect, answerKey };
  });
  const correctCount = rows.filter((r) => r.isCorrect).length;

  useEffect(() => {
    if (!state) return;
    for (const { q, isCorrect } of rows) {
      if (isCorrect) removeWrongQuestion(q.id);
      else addWrongQuestion(q.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  if (!state) {
    return (
      <div>
        <p>找不到測驗結果，可能是重新整理頁面導致資料遺失。</p>
        <Link to="/">回首頁</Link>
      </div>
    );
  }

  const percent = questions.length ? Math.round((correctCount / questions.length) * 100) : 0;

  return (
    <div>
      <Link to="/" className="back-link">
        ← 回首頁
      </Link>
      <h1>測驗結果</h1>
      <p className="score-summary">
        得分：{correctCount} / {questions.length}（{percent}%）
      </p>

      <ul className="result-list">
        {rows.map(({ q, userAnswer, isCorrect }, i) => (
          <li key={q.id} className={isCorrect ? "result-correct" : "result-wrong"}>
            <p className="result-index">
              第 {i + 1} 題　{isCorrect ? "✔ 答對" : "✘ 答錯"}
            </p>
            <p className="result-stem">{q.stem}</p>
            {q.type === "single" ? (
              <ul className="result-options">
                {Object.entries(q.options).map(([key, text]) => {
                  let cls = "";
                  if (key === q.answer) cls = "opt-correct";
                  else if (key === userAnswer) cls = "opt-wrong-selected";
                  return (
                    <li key={key} className={cls}>
                      <span className="choice-key">{key}</span>
                      {text}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="result-tf">
                <span>你的答案：{userAnswer === undefined ? "未作答" : TF_LABELS[userAnswer]}</span>
                <span>正確答案：{TF_LABELS[String(q.answer)]}</span>
              </p>
            )}
          </li>
        ))}
      </ul>

      <div className="result-actions">
        <Link to="/exam" className="primary-btn">
          再測一次
        </Link>
        <Link to="/">回首頁</Link>
      </div>
    </div>
  );
}
