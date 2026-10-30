/**
 * Candidate Exam Session Manager
 */

document.addEventListener("DOMContentLoaded", async () => {
  const sessionId = window.SESSION_ID;
  if (!sessionId) {
    alert("Invalid Exam Session ID!");
    window.location.href = "/";
    return;
  }

  // Initialize Proctoring Engine
  const proctor = new AIProctorEngine({ sessionId: sessionId });
  await proctor.start();

  // Exam state
  let questions = [];
  let currentIndex = 0;
  let answers = {};
  let timeLeftSeconds = 10 * 60; // 10 minutes

  // UI Elements
  const qTitle = document.getElementById("question-title");
  const qCategory = document.getElementById("question-category");
  const optionsList = document.getElementById("options-list");
  const qNavGrid = document.getElementById("q-nav-grid");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const submitBtn = document.getElementById("submit-exam-btn");
  const timerDisplay = document.getElementById("exam-timer");

  // Load Questions
  try {
    const res = await fetch(`/api/exam/${sessionId}/questions`);
    if (!res.ok) throw new Error("Could not load exam questions");
    const data = await res.json();
    questions = data.questions;

    buildQuestionNav();
    loadQuestion(0);
    startTimer();
  } catch (err) {
    console.error(err);
    alert("Error loading exam: " + err.message);
  }

  function buildQuestionNav() {
    qNavGrid.innerHTML = "";
    questions.forEach((q, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `nav-q-btn ${idx === 0 ? "current" : ""}`;
      btn.textContent = idx + 1;
      btn.addEventListener("click", () => loadQuestion(idx));
      qNavGrid.appendChild(btn);
    });
  }

  function loadQuestion(index) {
    if (index < 0 || index >= questions.length) return;
    currentIndex = index;
    const q = questions[index];

    qTitle.textContent = `Q${index + 1}. ${q.question_text}`;
    if (qCategory) qCategory.textContent = q.category || "General";

    optionsList.innerHTML = "";
    q.options.forEach((optText, optIdx) => {
      const label = document.createElement("label");
      label.className = "option-item";
      if (answers[q.id] === optIdx) {
        label.classList.add("selected");
      }

      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `question_${q.id}`;
      radio.value = optIdx;
      radio.checked = answers[q.id] === optIdx;
      radio.className = "option-radio";

      radio.addEventListener("change", () => {
        answers[q.id] = optIdx;
        updateNavButtons();
        // Update visual selection
        document.querySelectorAll(".option-item").forEach(el => el.classList.remove("selected"));
        label.classList.add("selected");
      });

      const span = document.createElement("span");
      span.textContent = optText;

      label.appendChild(radio);
      label.appendChild(span);
      optionsList.appendChild(label);
    });

    prevBtn.disabled = currentIndex === 0;
    if (currentIndex === questions.length - 1) {
      nextBtn.style.display = "none";
    } else {
      nextBtn.style.display = "inline-flex";
    }

    updateNavButtons();
  }

  function updateNavButtons() {
    const buttons = qNavGrid.querySelectorAll(".nav-q-btn");
    buttons.forEach((btn, idx) => {
      btn.classList.remove("current");
      if (idx === currentIndex) {
        btn.classList.add("current");
      }
      const qId = questions[idx].id;
      if (answers[qId] !== undefined) {
        btn.classList.add("answered");
      } else {
        btn.classList.remove("answered");
      }
    });
  }

  prevBtn.addEventListener("click", () => {
    if (currentIndex > 0) loadQuestion(currentIndex - 1);
  });

  nextBtn.addEventListener("click", () => {
    if (currentIndex < questions.length - 1) loadQuestion(currentIndex + 1);
  });

  submitBtn.addEventListener("click", () => {
    const answeredCount = Object.keys(answers).length;
    const confirmMsg = `You have answered ${answeredCount} of ${questions.length} questions. Are you sure you want to finalize and submit?`;
    if (confirm(confirmMsg)) {
      finishAndSubmit();
    }
  });

  function startTimer() {
    const timerInterval = setInterval(() => {
      if (timeLeftSeconds <= 0) {
        clearInterval(timerInterval);
        alert("Time is up! Your answers will be submitted automatically.");
        finishAndSubmit();
        return;
      }
      timeLeftSeconds--;
      const mins = Math.floor(timeLeftSeconds / 60);
      const secs = timeLeftSeconds % 60;
      timerDisplay.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

      if (timeLeftSeconds === 60) {
        proctor.showToast("⚠️ Warning: 1 minute remaining!", "warning");
      }
    }, 1000);
  }

  async function finishAndSubmit() {
    try {
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";

      const res = await fetch("/api/exam/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          answers: answers
        })
      });

      const data = await res.json();
      proctor.stop();
      window.location.href = `/result/${sessionId}`;
    } catch (err) {
      console.error(err);
      alert("Error submitting exam: " + err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Exam";
    }
  }

  // Fullscreen Enforcer Modal
  const fullscreenBtn = document.getElementById("reenter-fullscreen-btn");
  if (fullscreenBtn) {
    fullscreenBtn.addEventListener("click", () => {
      document.documentElement.requestFullscreen().then(() => {
        const modal = document.getElementById("fullscreen-modal");
        if (modal) modal.style.display = "none";
      }).catch(err => {
        console.warn("Fullscreen request error:", err);
      });
    });
  }
});
