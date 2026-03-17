/**
 * Replay page - screenshot slideshow player.
 *
 * Session data is read from data-session attribute on #replay-container.
 */

const replayContainer = document.getElementById("replay-container");
const SESSION_DATA = JSON.parse(replayContainer.dataset.session || "{}");

let currentStep = 0;
let isPlaying = true;
let playInterval = null;
let delay = 1000;
const preloadedImages = {};

const screenshot = document.getElementById("replay-screenshot");
const stepIndicator = document.getElementById("step-indicator");
const actionInfo = document.getElementById("action-info");
const playPauseBtn = document.getElementById("play-pause-btn");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const speedSelect = document.getElementById("speed-select");
const progressBar = document.getElementById("progress-bar");
const progressBarContainer = document.getElementById("progress-bar-container");

const totalSteps = SESSION_DATA.screenshotCount;

/* ── Helpers ── */

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getScreenshotUrl(step) {
  return `/sessions/${SESSION_DATA.id}/screenshots/${step}`;
}

function preloadImage(step) {
  if (preloadedImages[step]) return;
  const img = new Image();
  img.src = getScreenshotUrl(step);
  preloadedImages[step] = img;
}

function getActionLabel(action) {
  switch (action.type) {
    case "click":
      return `Click (${action.x}, ${action.y})`;
    case "hover":
      return `Hover (${action.x}, ${action.y})`;
    case "type":
      return `Type "${action.text}"`;
    case "press":
      return `Press ${action.key}`;
    case "scroll_up":
      return "Scroll Up";
    case "scroll_down":
      return "Scroll Down";
    case "goto":
      return `Go to ${action.url}`;
    case "go_back":
      return "Go back";
    case "go_forward":
      return "Go forward";
    case "finish":
      return "Finish";
    default:
      return action.type;
  }
}

function getActionBadgeClass(type) {
  if (type === "click" || type === "hover") return "badge-primary";
  if (type === "type" || type === "press") return "badge-secondary";
  if (type.startsWith("scroll")) return "badge-accent";
  if (type.startsWith("go") || type === "goto") return "badge-info";
  if (type === "finish") return "badge-success";
  return "badge-ghost";
}

/* ── Display ── */

function updateDisplay() {
  stepIndicator.textContent = `Step ${currentStep} of ${totalSteps - 1}`;

  const progress = totalSteps > 1 ? (currentStep / (totalSteps - 1)) * 100 : 0;
  progressBar.style.width = `${progress}%`;

  if (currentStep === 0) {
    actionInfo.innerHTML =
      '<span class="badge badge-ghost">Initial</span><span>Starting screenshot</span>';
  } else {
    const actionIndex = currentStep - 1;
    const action = SESSION_DATA.actions[actionIndex];
    if (action) {
      const badgeClass = getActionBadgeClass(action.type);
      const label = getActionLabel(action);
      const explanation = action.explanation || "\u2014";
      actionInfo.innerHTML = `<span class="badge ${badgeClass}">${label}</span><span>${esc(explanation)}</span>`;
    } else {
      actionInfo.innerHTML =
        '<span class="badge badge-ghost">Final</span><span>Final state</span>';
    }
  }

  if (currentStep + 1 < totalSteps) {
    preloadImage(currentStep + 1);
  }
}

function showScreenshot(step) {
  screenshot.classList.add("fading");
  setTimeout(() => {
    screenshot.src = getScreenshotUrl(step);
    screenshot.classList.remove("fading");
  }, 250);
}

/* ── Navigation ── */

function goToStep(step) {
  if (step < 0 || step >= totalSteps) return;
  currentStep = step;
  showScreenshot(currentStep);
  updateDisplay();
}

function nextStep() {
  if (currentStep < totalSteps - 1) {
    goToStep(currentStep + 1);
  } else if (isPlaying) {
    goToStep(0); // loop
  }
}

function prevStep() {
  if (currentStep > 0) {
    goToStep(currentStep - 1);
  }
}

/* ── Playback ── */

function startAutoPlay() {
  if (playInterval) clearInterval(playInterval);
  playInterval = setInterval(() => nextStep(), delay);
}

function stopAutoPlay() {
  if (playInterval) {
    clearInterval(playInterval);
    playInterval = null;
  }
}

function togglePlayPause() {
  isPlaying = !isPlaying;
  if (isPlaying) {
    playPauseBtn.innerHTML = '<i class="lni lni-pause"></i> Pause';
    startAutoPlay();
  } else {
    playPauseBtn.innerHTML = '<i class="lni lni-play"></i> Play';
    stopAutoPlay();
  }
}

/* ── Event listeners ── */

playPauseBtn.addEventListener("click", togglePlayPause);
prevBtn.addEventListener("click", prevStep);
nextBtn.addEventListener("click", nextStep);

speedSelect.addEventListener("change", (e) => {
  delay = parseInt(e.target.value);
  if (isPlaying) {
    stopAutoPlay();
    startAutoPlay();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    prevStep();
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    nextStep();
  } else if (e.key === " ") {
    e.preventDefault();
    togglePlayPause();
  }
});

progressBarContainer.addEventListener("click", (e) => {
  const rect = progressBarContainer.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const percent = clickX / rect.width;
  const targetStep = Math.round(percent * (totalSteps - 1));
  goToStep(targetStep);
});

/* ── Initialize ── */

goToStep(0);
if (isPlaying) {
  startAutoPlay();
}
