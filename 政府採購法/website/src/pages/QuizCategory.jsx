import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { getQuestionsByCategory } from "../data/repository";
import PracticeQuiz from "../components/PracticeQuiz";

export default function QuizCategory() {
  const { category: encodedCategory } = useParams();
  const category = decodeURIComponent(encodedCategory);
  const questions = useMemo(() => getQuestionsByCategory(category), [category]);

  if (questions.length === 0) {
    return (
      <div>
        <p>找不到類別「{category}」。</p>
        <Link to="/">回首頁</Link>
      </div>
    );
  }

  return <PracticeQuiz questions={questions} title={category} backTo="/" />;
}
