const grid = document.getElementById("grid");
const toast = document.getElementById("toast");
const targetLightsEl = document.getElementById("target-lights");
const targetCountEl = document.getElementById("target-count");
const categoryFiltersEl = document.getElementById("category-filters");
const createBtn = document.getElementById("create-btn");

let allLights = [];
let savedTargetIds = [];
let allThemes = [];
let allEffects = [];
let settings = { dynamic_mode: false, dynamic_interval: 8 };
let activeTab = "themes";
let activeCategory = "All";

function showToast(msg, isError = false) {
  toast.textContent = msg;
  toast.classList.remove("hidden");
  toast.style.background = isError ? "#c0392b" : "";
  setTimeout(() => toast.classList.add("hidden"), 3000);
}

async function api(path, options = {}) {
  const res = await fetch(`api/${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

function getSwatchColors(item) {
  if (item.slots) return item.slots.map((s) => s.color);
  if (item.colors) return item.colors;
  if (item.base_color) return [item.base_color];
  return ["#888"];
}

function swatchHtml(item) {
  return getSwatchColors(item)
    .map((c) => `<span style="background:${c}"></span>`)
    .join("");
}

function currentList() {
  return activeTab === "themes" ? allThemes : allEffects;
}

function itemCard(item, kind) {
  const el = document.createElement("div");
  el.className = "card";
  const tags = item.tags || [];
  el.innerHTML = `
    <div class="swatch">${swatchHtml(item)}</div>
    <div class="card-body">
      <span class="category-badge">${item.category || "Custom"}</span>
      <h3>${item.name}</h3>
      <p>${item.description || ""}</p>
      <div class="tags">${tags.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
      <div class="card-actions">
        <button class="btn btn-primary apply-btn">Apply</button>
        ${kind === "theme" ? '<button class="btn share-btn" title="Submit to community library">Share</button>' : ""}
        ${kind === "theme" && item.source !== "bundled" ? '<button class="btn btn-icon btn-danger delete-btn" title="Delete">Del</button>' : ""}
      </div>
    </div>
  `;
  el.querySelector(".apply-btn").addEventListener("click", () =>
    kind === "theme" ? applyTheme(item) : applyEffect(item)
  );
  const shareBtn = el.querySelector(".share-btn");
  if (shareBtn) shareBtn.addEventListener("click", () => shareTheme(item));
  const delBtn = el.querySelector(".delete-btn");
  if (delBtn) delBtn.addEventListener("click", () => deleteTheme(item));
  return el;
}

function renderGrid() {
  grid.innerHTML = "";
  const kind = activeTab === "themes" ? "theme" : "effect";
  const visible = activeCategory === "All"
    ? currentList()
    : currentList().filter((t) => (t.category || "Custom") === activeCategory);
  visible.forEach((item) => grid.appendChild(itemCard(item, kind)));
}

function renderCategoryFilters() {
  const categories = ["All", ...new Set(currentList().map((t) => t.category || "Custom"))];
  categoryFiltersEl.innerHTML = "";
  categories.forEach((cat) => {
    const btn = document.createElement("button");
    btn.className = "category-pill" + (cat === activeCategory ? " active" : "");
    btn.textContent = cat;
    btn.addEventListener("click", () => {
      activeCategory = cat;
      renderCategoryFilters();
      renderGrid();
    });
    categoryFiltersEl.appendChild(btn);
  });

  if (activeTab === "themes") {
    const datalist = document.getElementById("category-options");
    datalist.innerHTML = categories
      .filter((c) => c !== "All")
      .map((c) => `<option value="${c}"></option>`)
      .join("");
  }
}

async function loadThemes() {
  allThemes = await api("themes");
}

async function loadEffects() {
  allEffects = await api("effects");
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    activeTab = btn.dataset.tab;
    activeCategory = "All";
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
    createBtn.classList.toggle("hidden", activeTab !== "themes");
    renderCategoryFilters();
    renderGrid();
  });
});

async function deleteTheme(theme) {
  if (!confirm(`Delete "${theme.name}"?`)) return;
  try {
    await api(`themes/${theme.id}`, { method: "DELETE" });
    showToast("Theme deleted");
    await loadThemes();
    renderCategoryFilters();
    renderGrid();
  } catch (e) {
    showToast(e.message, true);
  }
}

async function shareTheme(theme) {
  try {
    const { url } = await api(`themes/${theme.id}/submit-url`);
    window.open(url, "_blank", "noopener");
  } catch (e) {
    showToast(e.message, true);
  }
}

async function applyTheme(theme) {
  if (!savedTargetIds.length) {
    showToast("Select your target lights in Controls first", true);
    return;
  }
  try {
    const res = await api(`themes/${theme.id}/apply`, {
      method: "POST",
      body: JSON.stringify({ entity_ids: savedTargetIds }),
    });
    showToast(res.dynamic ? `Cycling "${theme.name}"` : `Applied "${theme.name}"`);
    refreshRunningStatus();
  } catch (e) {
    showToast(e.message, true);
  }
}

async function applyEffect(effect) {
  if (!savedTargetIds.length) {
    showToast("Select your target lights in Controls first", true);
    return;
  }
  try {
    await api(`effects/${effect.id}/apply`, {
      method: "POST",
      body: JSON.stringify({ entity_ids: savedTargetIds }),
    });
    showToast(`Started "${effect.name}"`);
    refreshRunningStatus();
  } catch (e) {
    showToast(e.message, true);
  }
}

// --- Running banner ---

const runningBanner = document.getElementById("running-banner");
const runningText = document.getElementById("running-text");

async function refreshRunningStatus() {
  try {
    const status = await api("dynamic/status");
    if (status.running) {
      runningText.textContent = status.kind === "theme"
        ? `Cycling: ${status.name}`
        : `Effect: ${status.name}`;
      runningBanner.classList.remove("hidden");
    } else {
      runningBanner.classList.add("hidden");
    }
  } catch (e) {
    // non-critical, ignore
  }
}

document.getElementById("running-stop").addEventListener("click", async () => {
  try {
    await api("dynamic/stop", { method: "POST" });
    refreshRunningStatus();
  } catch (e) {
    showToast(e.message, true);
  }
});

// --- Controls bar (Target Lights + Dynamic Mode) ---

const controlsBarEl = document.getElementById("controls-bar");
const controlsToggleEl = document.getElementById("controls-toggle");
const controlsSummaryEl = document.getElementById("controls-summary");
const dynamicToggleEl = document.getElementById("dynamic-toggle");
const dynamicIntervalEl = document.getElementById("dynamic-interval");

function updateTargetCount() {
  targetCountEl.textContent = savedTargetIds.length
    ? `${savedTargetIds.length} selected`
    : "none selected";
  updateControlsSummary();
}

function updateControlsSummary() {
  const lightsPart = `${savedTargetIds.length} light${savedTargetIds.length === 1 ? "" : "s"}`;
  const dynamicPart = `Dynamic ${settings.dynamic_mode ? "On" : "Off"}`;
  controlsSummaryEl.textContent = `${lightsPart} · ${dynamicPart}`;
}

function setControlsCollapsed(collapsed) {
  controlsBarEl.classList.toggle("collapsed", collapsed);
  controlsToggleEl.setAttribute("aria-expanded", String(!collapsed));
  localStorage.setItem("controlsCollapsed", collapsed ? "1" : "0");
}

controlsToggleEl.addEventListener("click", () => {
  setControlsCollapsed(!controlsBarEl.classList.contains("collapsed"));
});

function renderTargetLights() {
  targetLightsEl.innerHTML = "";
  allLights.forEach((light) => {
    const row = document.createElement("label");
    row.className = "light-row";
    const checked = savedTargetIds.includes(light.entity_id);
    row.innerHTML = `<input type="checkbox" value="${light.entity_id}" ${checked ? "checked" : ""}/> ${light.name}`;
    row.querySelector("input").addEventListener("change", onTargetLightsChanged);
    targetLightsEl.appendChild(row);
  });
  updateTargetCount();
}

async function onTargetLightsChanged() {
  savedTargetIds = Array.from(targetLightsEl.querySelectorAll("input:checked")).map((i) => i.value);
  updateTargetCount();
  try {
    await api("target-lights", {
      method: "POST",
      body: JSON.stringify({ entity_ids: savedTargetIds }),
    });
  } catch (e) {
    showToast(e.message, true);
  }
}

dynamicToggleEl.addEventListener("change", async () => {
  try {
    settings = await api("settings", {
      method: "POST",
      body: JSON.stringify({ dynamic_mode: dynamicToggleEl.checked }),
    });
    updateControlsSummary();
    refreshRunningStatus();
  } catch (e) {
    showToast(e.message, true);
  }
});

dynamicIntervalEl.addEventListener("change", async () => {
  const value = parseInt(dynamicIntervalEl.value, 10);
  try {
    settings = await api("settings", {
      method: "POST",
      body: JSON.stringify({ dynamic_interval: value }),
    });
  } catch (e) {
    showToast(e.message, true);
    dynamicIntervalEl.value = settings.dynamic_interval;
  }
});

function renderLightCheckboxes(container, lights, checkedIds) {
  container.innerHTML = "";
  lights.forEach((light) => {
    const row = document.createElement("label");
    row.className = "light-row";
    const checked = checkedIds.includes(light.entity_id);
    row.innerHTML = `<input type="checkbox" value="${light.entity_id}" ${checked ? "checked" : ""}/> ${light.name}`;
    container.appendChild(row);
  });
}

function getCheckedEntityIds(container) {
  return Array.from(container.querySelectorAll("input:checked")).map((i) => i.value);
}

const createModal = document.getElementById("create-modal");
const createLightsEl = document.getElementById("create-lights");

createBtn.addEventListener("click", () => {
  document.getElementById("create-name").value = "";
  document.getElementById("create-desc").value = "";
  document.getElementById("create-category").value = "";
  document.getElementById("create-tags").value = "";
  renderLightCheckboxes(createLightsEl, allLights, savedTargetIds);
  createModal.classList.remove("hidden");
});

document.getElementById("create-confirm").addEventListener("click", async () => {
  const name = document.getElementById("create-name").value.trim();
  const description = document.getElementById("create-desc").value.trim();
  const category = document.getElementById("create-category").value.trim() || "Custom";
  const tags = document
    .getElementById("create-tags")
    .value.split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const entityIds = getCheckedEntityIds(createLightsEl);

  if (!name) return showToast("Name is required", true);
  if (!entityIds.length) return showToast("Select at least one light", true);

  try {
    await api("themes/capture", {
      method: "POST",
      body: JSON.stringify({ name, description, category, tags, entity_ids: entityIds }),
    });
    showToast("Theme saved");
    createModal.classList.add("hidden");
    await loadThemes();
    renderCategoryFilters();
    renderGrid();
  } catch (e) {
    showToast(e.message, true);
  }
});

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.getElementById(btn.dataset.close).classList.add("hidden");
  });
});

async function init() {
  setControlsCollapsed(localStorage.getItem("controlsCollapsed") !== "0");

  try {
    [allLights, savedTargetIds, settings] = await Promise.all([
      api("lights"),
      api("target-lights"),
      api("settings"),
    ]);
    renderTargetLights();
    dynamicToggleEl.checked = !!settings.dynamic_mode;
    dynamicIntervalEl.value = settings.dynamic_interval;
    updateControlsSummary();
  } catch (e) {
    showToast(e.message, true);
  }

  try {
    await Promise.all([loadThemes(), loadEffects()]);
    renderCategoryFilters();
    renderGrid();
  } catch (e) {
    showToast(e.message, true);
  }

  refreshRunningStatus();
}

init();
