let selectedDifficulty = "easy";
let selectedQuestions = 3;
let quizData = null;
let userAnswers = [];
let quizSubmitted = false;
let timerInterval = null;
let remainingSeconds = 0;

const setupScreen = document.getElementById("setupScreen");
const quizScreen = document.getElementById("quizScreen");
const topicInput = document.getElementById("topic");
const startBtn = document.getElementById("startBtn");
const setupError = document.getElementById("setupError");
const setupHelper = document.getElementById("setupHelper");
const quizTopic = document.getElementById("quizTopic");
const questionsList = document.getElementById("questionsList");
const submitBtn = document.getElementById("submitBtn");
const scoreBox = document.getElementById("scoreBox");
const scoreValue = document.getElementById("scoreValue");
const retryBtn = document.getElementById("retryBtn");
const progressBar = document.getElementById("progressBar");
const timerDisplay =
  document.getElementById("timerDisplay") || document.getElementById("timer");

function setupButtons(groupId, setter) {
  const buttons = document.querySelectorAll(`#${groupId} .btn`);

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((button) => button.classList.remove("active"));
      btn.classList.add("active");
      setter(btn.dataset.value);
    });
  });

  if (buttons.length > 0) {
    buttons[0].classList.add("active");
  }
}

setupButtons("difficulty", (val) => {
  selectedDifficulty = val;
});

setupButtons("questions", (val) => {
  selectedQuestions = Number(val);
});

function getTimerSeconds(questionCount) {
  if (questionCount === 3) return 120;
  if (questionCount === 5) return 180;
  return 360;
}

function formatTime(totalSeconds) {
  const safeSeconds = Math.max(totalSeconds, 0);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function updateTimerUI() {
  if (timerDisplay) {
    timerDisplay.textContent = formatTime(remainingSeconds);
  }
}

function stopTimer() {
  clearInterval(timerInterval);
}

function startTimer() {
  stopTimer();
  remainingSeconds = getTimerSeconds(quizData?.questions?.length || selectedQuestions);
  updateTimerUI();

  timerInterval = setInterval(() => {
    remainingSeconds -= 1;
    updateTimerUI();

    if (remainingSeconds <= 0) {
      stopTimer();
      submitQuiz(true);
    }
  }, 1000);
}

function updateProgressBar() {
  const answeredCount = userAnswers.filter(Boolean).length;
  const total = quizData?.questions?.length || selectedQuestions;

  const segments = progressBar.querySelectorAll(".progress-segment");
  segments.forEach((segment, index) => {
    if (index < answeredCount) {
      segment.classList.add("filled");
    } else {
      segment.classList.remove("filled");
    }
  });
}

function buildProgressBar(totalQuestions) {
  progressBar.innerHTML = "";
  progressBar.style.setProperty("--segments", totalQuestions);

  for (let i = 0; i < totalQuestions; i += 1) {
    const segment = document.createElement("div");
    segment.className = "progress-segment";
    progressBar.appendChild(segment);
  }

  updateProgressBar();
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderQuestions() {
  questionsList.innerHTML = "";

  quizData.questions.forEach((q, i) => {
    const div = document.createElement("div");
    div.className = "question";

    const options = q.options
      .map((opt) => {
        return `<button class="answer" type="button" data-q="${i}" data-val="${escapeHtml(opt)}">${escapeHtml(opt)}</button>`;
      })
      .join("");

    div.innerHTML = `
      <p>${escapeHtml(q.question)}</p>
      ${options}
      <div class="explanation-box hidden">
        <div class="explanation-text"></div>
      </div>
    `;

    questionsList.appendChild(div);
  });

  document.querySelectorAll(".answer").forEach((el) => {
    el.addEventListener("click", () => {
      if (quizSubmitted) return;

      const q = Number(el.dataset.q);
      const val = el.dataset.val;
      userAnswers[q] = val;

      document
        .querySelectorAll(`.answer[data-q="${q}"]`)
        .forEach((x) => x.classList.remove("selected"));

      el.classList.add("selected");
      updateProgressBar();
    });
  });
}

async function startQuiz() {
  const topic = topicInput.value.trim();

  if (!topic) {
    if (setupError) setupError.textContent = "Enter a topic first.";
    return;
  }

  if (setupError) setupError.textContent = "";
  if (setupHelper) setupHelper.textContent = "Building your quiz...";
  startBtn.disabled = true;
  startBtn.textContent = "Loading...";

  try {
    const response = await fetch("http://127.0.0.1:5000/api/quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic,
        difficulty: selectedDifficulty,
        num_questions: selectedQuestions,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not generate quiz.");
    }

    quizData = data;
    userAnswers = new Array(quizData.questions.length).fill(null);
    quizSubmitted = false;

    if (quizTopic) quizTopic.textContent = quizData.topic;
    buildProgressBar(quizData.questions.length);
    renderQuestions();

    setupScreen.classList.add("hidden");
    quizScreen.classList.remove("hidden");
    scoreBox.classList.add("hidden");
    submitBtn.classList.remove("hidden");

    startTimer();
  } catch (error) {
    if (setupError) {
      setupError.textContent =
        error.message || "Something went wrong while creating the quiz.";
    }
    if (setupHelper) {
      setupHelper.textContent = "Pick a topic and Athena will build your quiz.";
    }
  } finally {
    startBtn.disabled = false;
    startBtn.textContent = "Start Quiz";
  }
}

function revealResults(gradedData) {
  quizSubmitted = true;
  stopTimer();

  const questions = quizData.questions;
  const cards = document.querySelectorAll(".question");

  gradedData.results.forEach((result, index) => {
    const card = cards[index];
    const options = card.querySelectorAll(".answer");
    const explanationBox = card.querySelector(".explanation-box");
    const explanationText = card.querySelector(".explanation-text");
    const correctAnswer = questions[index].correct_answer;

    options.forEach((option) => {
      const value = option.dataset.val;
      option.disabled = true;

      if (value === correctAnswer) {
        option.classList.add("correct");
      }

      if (value === result.user_answer && result.user_answer !== correctAnswer) {
        option.classList.add("incorrect");
      }
    });

    explanationBox.classList.remove("hidden");
    explanationText.innerHTML = `<strong>Explanation:</strong> ${escapeHtml(
      result.explanation || `Correct answer: ${correctAnswer}`
    )}`;
  });

  scoreValue.textContent = `${gradedData.score} / ${gradedData.total}`;
  scoreBox.classList.remove("hidden");
  submitBtn.classList.add("hidden");

  const segments = progressBar.querySelectorAll(".progress-segment");
  segments.forEach((segment) => segment.classList.add("filled"));
}

async function submitQuiz(autoSubmitted = false) {
  if (!quizData || quizSubmitted) return;

  if (!autoSubmitted && userAnswers.some((answer) => !answer)) {
    const shouldContinue = window.confirm(
      "You still have unanswered questions. Submit anyway?"
    );
    if (!shouldContinue) return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = autoSubmitted ? "Time's up..." : "Submitting...";

  try {
    const response = await fetch("http://127.0.0.1:5000/api/grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quiz_data: quizData,
        user_answers: userAnswers.map((answer) => answer || ""),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not grade quiz.");
    }

    revealResults(data);
  } catch (error) {
    alert(error.message || "Something went wrong while grading the quiz.");
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit";
  }
}

function resetToSetup() {
  stopTimer();
  quizData = null;
  userAnswers = [];
  quizSubmitted = false;
  topicInput.value = "";
  questionsList.innerHTML = "";

  if (setupError) setupError.textContent = "";
  if (setupHelper) {
    setupHelper.textContent = "Pick a topic and Athena will build your quiz.";
  }

  submitBtn.disabled = false;
  submitBtn.textContent = "Submit";
  scoreBox.classList.add("hidden");
  quizScreen.classList.add("hidden");
  setupScreen.classList.remove("hidden");
}

startBtn.addEventListener("click", startQuiz);
submitBtn.addEventListener("click", () => submitQuiz(false));
retryBtn.addEventListener("click", resetToSetup);