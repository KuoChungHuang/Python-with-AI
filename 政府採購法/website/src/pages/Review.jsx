import { useMemo } from "react";
import { Link } from "react-router-dom";
import { getQuestionsByIds } from "../data/repository";
import { getWrongQuestionIds } from "../data/storage";
import PracticeQuiz from "../components/PracticeQuiz";

export default function Review() {
  const questions = useMemo(() => getQuestionsByIds(getWrongQuestionIds()), []);

  if (questions.length === 0) {
    return (
      <div>
        <Link to="/" className="back-link">
          ← 回首頁
        </Link>
        <h1>錯題本</h1>
        <p>目前錯題本是空的，練習時答錯的題目會自動加進來。</p>
      </div>
    );
  }

  return <PracticeQuiz questions={questions} title={`錯題本（${questions.length} 題）`} backTo="/" />;
}
