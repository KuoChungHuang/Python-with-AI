const TF_LABELS = { true: "正確 (O)", false: "錯誤 (X)" };

export default function ExamQuestionView({ question, value, onChange }) {
  const isTf = question.type === "tf";
  const choices = isTf
    ? [true, false]
    : Object.entries(question.options).map(([key, text]) => ({ key, text }));

  function choiceKey(choice) {
    return isTf ? String(choice) : choice.key;
  }

  return (
    <div className="question-view">
      <p className="question-stem">{question.stem}</p>
      <div className="question-choices">
        {choices.map((choice) => {
          const key = choiceKey(choice);
          const isSelected = value === key;
          return (
            <button
              key={key}
              type="button"
              className={`choice-btn${isSelected ? " selected" : ""}`}
              onClick={() => onChange(key)}
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
    </div>
  );
}
