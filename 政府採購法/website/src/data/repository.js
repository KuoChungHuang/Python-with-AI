import questions from "./questions.json";

export function getCategories() {
  const seen = [];
  for (const q of questions) {
    if (!seen.includes(q.category)) seen.push(q.category);
  }
  return seen;
}

export function getQuestionsByCategory(category) {
  return questions.filter((q) => q.category === category);
}

export function getQuestionById(id) {
  return questions.find((q) => q.id === id);
}

export function getQuestionsByIds(ids) {
  const idSet = new Set(ids);
  return questions.filter((q) => idSet.has(q.id));
}

export function getRandomQuestions(n, category = null) {
  const pool = category ? getQuestionsByCategory(category) : questions;
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, n);
}

export function getTotalCount() {
  return questions.length;
}
