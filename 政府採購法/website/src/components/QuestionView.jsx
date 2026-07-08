import { useState, useEffect } from "react";

const TF_LABELS = { true: "正確 (O)", false: "錯誤 (X)" };

export default function QuestionView({ question, onAnswered }) {
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    setSelected(null);
  }, [question.id]);

  if (!question) return null;

  const isTf = question.type === "tf";
  const choices = isTf
    ? [true, false]
    : Object.entries(question.options).map(([key, text]) => ({ key, text }));

  function isCorrectChoice(choice) {
    return isTf ? choice === question.answer : choice.key === question.answer;
  }

  function choiceKey(choice) {
    return isTf ? String(choice) : choice.key;
  }

  const answerKey = isTf ? String(question.answer) : question.answer;

  function handleSelect(choice) {
    if (selected !== null) return;
    const key = choiceKey(choice);
    setSelected(key);
    onAnswered?.(key === answerKey);
  }

  const isSelectedCorrect = selected !== null && selected === answerKey;

  return (
    <div className="question-view">
      <p className="question-stem">{question.stem}</p>
      <div className="question-choices">
        {choices.map((choice) => {
          const key = choiceKey(choice);
          const correct = isCorrectChoice(choice);
          const isSelected = selected === key;
          let className = "choice-btn";
          if (selected !== null) {
            if (correct) className += " correct";
            else if (isSelected) className += " wrong";
          }
          return (
            <button
              key={key}
              type="button"
              className={className}
              onClick={() => handleSelect(choice)}
              disabled={selected !== null}
            >
              {isTf ? (
                TF_LABELS[key]
              ) : (
                <>
                  <span className="choice-key">{choice.key}</span>
                  {choice.text}
                </>
              )}
            </button>
          );
        })}
      </div>
      {selected !== null && (
        <p className={`feedback ${isSelectedCorrect ? "feedback-correct" : "feedback-wrong"}`}>
          {isSelectedCorrect
            ? "答對了！"
            : isTf
              ? `答錯了，正確答案是「${TF_LABELS[question.answer]}」。`
              : `答錯了，正確答案是 ${question.answer}。`}
        </p>
      )}
    </div>
  );
}
