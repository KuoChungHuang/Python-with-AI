const WRONG_KEY = "gpa-quiz-wrong-questions";

export function getWrongQuestionIds() {
  try {
    const raw = localStorage.getItem(WRONG_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addWrongQuestion(id) {
  const ids = getWrongQuestionIds();
  if (!ids.includes(id)) {
    ids.push(id);
    localStorage.setItem(WRONG_KEY, JSON.stringify(ids));
  }
}

export function removeWrongQuestion(id) {
  const ids = getWrongQuestionIds().filter((x) => x !== id);
  localStorage.setItem(WRONG_KEY, JSON.stringify(ids));
}

export function clearWrongQuestions() {
  localStorage.removeItem(WRONG_KEY);
}
