/**
 * Annotation page - coordinate picker, action selector, crosshair, HTMX handlers.
 *
 * Viewport dimensions are read from data-vw / data-vh attributes on #app-root.
 */

const appRoot = document.getElementById("app-root");
const VW = parseInt(appRoot.dataset.vw || "1280", 10);
const VH = parseInt(appRoot.dataset.vh || "900", 10);

let selectedAction = null;
let coordX = 0;
let coordY = 0;

/* ── Action selection ── */

function selectAction(type) {
  selectedAction = type;

  // Update chip visuals
  document.querySelectorAll(".action-chip").forEach((c) => c.classList.remove("active"));
  const chip = document.querySelector(`[data-action="${type}"]`);
  if (chip) chip.classList.add("active");

  // Show the correct parameter panel
  document.querySelectorAll(".param-panel").forEach((p) => p.classList.add("hidden"));
  const panel = document.getElementById(`params-${type}`);
  if (panel) panel.classList.remove("hidden");

  // Show submit area
  const submitArea = document.getElementById("submit-area");
  if (submitArea) submitArea.classList.remove("hidden");

  const typeInput = document.getElementById("action-type-input");
  if (typeInput) typeInput.value = type;

  // Check if this action needs coordinates
  const needsCoords = type === "click" || type === "hover";
  const area = document.getElementById("screenshot-area");
  if (area) area.style.cursor = needsCoords ? "crosshair" : "default";

  const coordInfo = document.getElementById("coord-info");
  if (coordInfo) coordInfo.classList.toggle("hidden", !needsCoords);
}

/* ── Event delegation for action chips ── */

document.addEventListener("click", (e) => {
  const target = e.target;
  const chip = target.closest("[data-action]");
  if (!chip || !chip.classList.contains("action-chip")) return;

  const action = chip.dataset.action;
  if (action) selectAction(action);
});

/* ── Screenshot click handler for coordinate capture ── */

const screenshotArea = document.getElementById("screenshot-area");

if (screenshotArea) {
  screenshotArea.addEventListener("click", function (e) {
    if (selectedAction !== "click" && selectedAction !== "hover") return;

    const img = this.querySelector("img");
    if (!img) return;

    const rect = img.getBoundingClientRect();
    const rx = e.clientX - rect.left;
    const ry = e.clientY - rect.top;
    coordX = Math.round(rx * (VW / rect.width));
    coordY = Math.round(ry * (VH / rect.height));

    // Update display
    const coordDisplay = document.getElementById("coord-display");
    if (coordDisplay) coordDisplay.textContent = `${coordX}, ${coordY}`;

    const inputX = document.getElementById("input-x");
    const inputY = document.getElementById("input-y");
    if (inputX) inputX.value = String(coordX);
    if (inputY) inputY.value = String(coordY);

    // Visual dot + crosshair lines
    this.querySelectorAll(".click-dot, .crosshair-h, .crosshair-v").forEach((d) => d.remove());
    this.style.position = "relative";

    const dotLeft = rx + img.offsetLeft;
    const dotTop = ry + img.offsetTop - this.scrollTop;

    const dot = document.createElement("div");
    dot.className = "click-dot";
    dot.style.left = `${dotLeft}px`;
    dot.style.top = `${dotTop}px`;
    this.appendChild(dot);

    const hLine = document.createElement("div");
    hLine.className = "crosshair-h";
    hLine.style.top = `${dotTop}px`;
    hLine.style.left = `${img.offsetLeft}px`;
    hLine.style.width = `${img.clientWidth}px`;
    this.appendChild(hLine);

    const vLine = document.createElement("div");
    vLine.className = "crosshair-v";
    vLine.style.left = `${dotLeft}px`;
    vLine.style.top = `${img.offsetTop}px`;
    vLine.style.height = `${img.clientHeight}px`;
    this.appendChild(vLine);
  });

  /* ── Live crosshair that follows mouse on screenshot ── */

  screenshotArea.addEventListener("mousemove", function (e) {
    if (selectedAction !== "click" && selectedAction !== "hover") return;

    const img = this.querySelector("img");
    if (!img) return;

    const rect = img.getBoundingClientRect();
    const rx = e.clientX - rect.left;
    const ry = e.clientY - rect.top;

    // Only show when hovering over the image
    if (rx < 0 || ry < 0 || rx > rect.width || ry > rect.height) {
      this.querySelectorAll(".crosshair-live-h, .crosshair-live-v").forEach((d) => d.remove());
      return;
    }

    this.style.position = "relative";
    this.querySelectorAll(".crosshair-live-h, .crosshair-live-v").forEach((d) => d.remove());

    const posLeft = rx + img.offsetLeft;
    const posTop = ry + img.offsetTop - this.scrollTop;

    const lh = document.createElement("div");
    lh.className = "crosshair-live-h";
    lh.style.top = `${posTop}px`;
    lh.style.left = `${img.offsetLeft}px`;
    lh.style.width = `${img.clientWidth}px`;
    this.appendChild(lh);

    const lv = document.createElement("div");
    lv.className = "crosshair-live-v";
    lv.style.left = `${posLeft}px`;
    lv.style.top = `${img.offsetTop}px`;
    lv.style.height = `${img.clientHeight}px`;
    this.appendChild(lv);
  });

  screenshotArea.addEventListener("mouseleave", function () {
    this.querySelectorAll(".crosshair-live-h, .crosshair-live-v").forEach((d) => d.remove());
  });
}

/* ── HTMX swap handler: clear dots and reset cursor ── */

document.body.addEventListener("htmx:afterSwap", (e) => {
  const detail = e.detail;
  if (detail?.target?.id === "screenshot-area") {
    document
      .querySelectorAll(".click-dot, .crosshair-h, .crosshair-v, .crosshair-live-h, .crosshair-live-v")
      .forEach((d) => d.remove());

    // Reset form state
    selectedAction = null;
    document.querySelectorAll(".action-chip").forEach((c) => c.classList.remove("active"));
    document.querySelectorAll(".param-panel").forEach((p) => p.classList.add("hidden"));

    const submitArea = document.getElementById("submit-area");
    if (submitArea) submitArea.classList.add("hidden");

    const area = document.getElementById("screenshot-area");
    if (area) area.style.cursor = "default";

    const exp = document.getElementById("explanation-input");
    if (exp) exp.value = "";
  }
});
