import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import QuizCategory from "./pages/QuizCategory";
import QuizRandom from "./pages/QuizRandom";
import Exam from "./pages/Exam";
import Review from "./pages/Review";
import Result from "./pages/Result";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/quiz/random" element={<QuizRandom />} />
      <Route path="/quiz/:category" element={<QuizCategory />} />
      <Route path="/exam" element={<Exam />} />
      <Route path="/review" element={<Review />} />
      <Route path="/result" element={<Result />} />
    </Routes>
  );
}

export default App;
