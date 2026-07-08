import { useState } from "react";
import { Link } from "react-router-dom";
import { getCategories, getRandomQuestions } from "../data/repository";
import PracticeQuiz from "../components/PracticeQuiz";

const COUNT_OPTIONS = [10, 20, 50];

export default function QuizRandom() {
  const categories = getCategories();
  const [category, setCategory] = useState("all");
  const [count, setCount] = useState(10);
  const [session, setSession] = useState(null);

  if (session) {
    return <PracticeQuiz questions={session} title="隨機測驗" backTo="/" />;
  }

  function start() {
    const qs = getRandomQuestions(count, category === "all" ? null : category);
    setSession(qs);
  }

  return (
    <div>
      <Link to="/" className="back-link">
        ← 回首頁
      </Link>
      <h1>隨機測驗</h1>
      <p>從題庫中隨機抽題練習，答題後立即顯示對錯。</p>

      <div className="settings-form">
        <label>
          類別
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="all">全部類別</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </label>

        <label>
          題數
          <select value={count} onChange={(e) => setCount(Number(e.target.value))}>
            {COUNT_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n} 題
              </option>
            ))}
          </select>
        </label>

        <button type="button" className="primary-btn" onClick={start}>
          開始測驗
        </button>
      </div>
    </div>
  );
}
