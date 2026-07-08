import { Link } from "react-router-dom";
import { getCategories, getQuestionsByCategory } from "../data/repository";
import { getWrongQuestionIds } from "../data/storage";

export default function Home() {
  const categories = getCategories();
  const wrongCount = getWrongQuestionIds().length;

  return (
    <div>
      <h1>政府採購法練習測驗</h1>
      <p>選擇一個類別開始練習，或使用下方的其他練習模式。</p>

      <div className="mode-links">
        <Link to="/quiz/random" className="mode-link">
          隨機測驗
        </Link>
        <Link to="/exam" className="mode-link">
          模擬考
        </Link>
        {wrongCount > 0 ? (
          <Link to="/review" className="mode-link">
            錯題本（{wrongCount}）
          </Link>
        ) : (
          <span className="mode-link disabled" title="還沒有錯題">
            錯題本（0）
          </span>
        )}
      </div>

      <ul className="category-list">
        {categories.map((cat) => {
          const count = getQuestionsByCategory(cat).length;
          return (
            <li key={cat}>
              <Link to={`/quiz/${encodeURIComponent(cat)}`}>
                <span className="category-name">{cat}</span>
                <span className="category-count">{count} 題</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
