import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getRandomQuestions } from "../data/repository";
import ExamQuestionView from "../components/ExamQuestionView";

const PRESETS = [
  { count: 10, minutes: 15 },
  { count: 20, minutes: 30 },
  { count: 50, minutes: 60 },
];

function formatTime(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function Exam() {
  const navigate = useNavigate();
  const [preset, setPreset] = useState(PRESETS[0]);
  const [session, setSession] = useState(null);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!session) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [session]);

  useEffect(() => {
    if (session && now >= session.deadline) {
      finishExam();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [now]);

  function startExam() {
    const questions = getRandomQuestions(preset.count);
    setSession({ questions, deadline: Date.now() + preset.minutes * 60 * 1000 });
    setAnswers({});
    setIndex(0);
    setNow(Date.now());
  }

  function finishExam() {
    navigate("/result", { state: { questions: session.questions, answers } });
  }

  function handleSubmitClick() {
    const answeredCount = Object.keys(answers).length;
    const total = session.questions.length;
    if (
      answeredCount < total &&
      !window.confirm(`還有 ${total - answeredCount} 題未作答，確定要交卷嗎？`)
    ) {
      return;
    }
    finishExam();
  }

  if (!session) {
    return (
      <div>
        <Link to="/" className="back-link">
          ← 回首頁
        </Link>
        <h1>模擬考</h1>
        <p>固定題數＋倒數計時，作答時不會立即顯示對錯，交卷後才看得到成績。</p>

        <div className="settings-form">
          <label>
            考試組合
            <select
              value={preset.count}
              onChange={(e) =>
                setPreset(PRESETS.find((p) => p.count === Number(e.target.value)))
              }
            >
              {PRESETS.map((p) => (
                <option key={p.count} value={p.count}>
                  {p.count} 題／{p.minutes} 分鐘
                </option>
              ))}
            </select>
          </label>

          <button type="button" className="primary-btn" onClick={startExam}>
            開始考試
          </button>
        </div>
      </div>
    );
  }

  const question = session.questions[index];
  const remaining = session.deadline - now;

  return (
    <div>
      <div className="quiz-header exam-header">
        <span className="timer">剩餘時間 {formatTime(remaining)}</span>
        <h2>模擬考</h2>
        <p className="progress">
          第 {index + 1} / {session.questions.length} 題（已作答 {Object.keys(answers).length} 題）
        </p>
      </div>

      <ExamQuestionView
        key={question.id}
        question={question}
        value={answers[question.id]}
        onChange={(val) => setAnswers((prev) => ({ ...prev, [question.id]: val }))}
      />

      <div className="quiz-nav">
        <button
          type="button"
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
        >
          上一題
        </button>
        {index === session.questions.length - 1 ? (
          <button type="button" className="primary-btn" onClick={handleSubmitClick}>
            交卷
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setIndex((i) => Math.min(session.questions.length - 1, i + 1))}
          >
            下一題
          </button>
        )}
      </div>
    </div>
  );
}
