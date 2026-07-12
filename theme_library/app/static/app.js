const grid = document.getElementById("grid");
const toast = document.getElementById("toast");
const targetLightsEl = document.getElementById("target-lights");
const targetCountEl = document.getElementById("target-count");
const categoryFiltersEl = document.getElementById("category-filters");

let allLights = [];
let savedTargetIds = [];
let allThemes = [];
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

function swatchHtml(slots) {
  return slots
    .map((s) => `<span style="background:${s.color}"></span>`)
    .join("");
}

function themeCard(theme) {
  const el = document.createElement("div");
  el.className = "card";
  el.innerHTML = `
    <div class="swatch">${swatchHtml(theme.slots)}</div>
    <div class="card-body">
      <span class="category-badge">${theme.category || "Custom"}</span>
      <h3>${theme.name}</h3>
      <p>${theme.description || ""}</p>
      <div class="tags">${(theme.tags || []).map((t) => `<span class="tag">${t}</span>`).join("")}</div>
      <div class="card-actions">
        <button class="btn btn-primary apply-btn">Apply</button>
        <button class="btn share-btn" title="Submit to community library">Share</button>
        ${theme.source !== "bundled" ? '<button class="btn btn-icon btn-danger delete-btn" title="Delete">Del</button>' : ""}
      </div>
    </div>
  `;
  el.querySelector(".apply-btn").addEventListener("click", () => applyTheme(theme));
  el.querySelector(".share-btn").addEventListener("click", () => shareTheme(theme));
  const delBtn = el.querySelector(".delete-btn");
  if (delBtn) delBtn.addEventListener("click", () => deleteTheme(theme));
  return el;
}

function renderGrid() {
  grid.innerHTML = "";
  const visible = activeCategory === "All"
    ? allThemes
    : allThemes.filter((t) => (t.category || "Custom") === activeCategory);
  visible.forEach((theme) => grid.appendChild(themeCard(theme)));
}

function renderCategoryFilters() {
  const categories = ["All", ...new Set(allThemes.map((t) => t.category || "Custom"))];
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

  const datalist = document.getElementById("category-options");
  datalist.innerHTML = categories
    .filter((c) => c !== "All")
    .map((c) => `<option value="${c}"></option>`)
    .join("");
}

async function loadThemes() {
  allThemes = await api("themes");
  renderCategoryFilters();
  renderGrid();
}

async function deleteTheme(theme) {
  if (!confirm(`Delete "${theme.name}"?`)) return;
  try {
    await api(`themes/${theme.id}`, { method: "DELETE" });
    showToast("Theme deleted");
    loadThemes();
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
    showToast("Select your target lights above first", true);
    return;
  }
  try {
    await api(`themes/${theme.id}/apply`, {
      method: "POST",
      body: JSON.stringify({ entity_ids: savedTargetIds }),
    });
    showToast(`Applied "${theme.name}"`);
  } catch (e) {
    showToast(e.message, true);
  }
}

function updateTargetCount() {
  targetCountEl.textContent = savedTargetIds.length
    ? `${savedTargetIds.length} selected`
    : "none selected";
}

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

document.getElementById("create-btn").addEventListener("click", () => {
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
    loadThemes();
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
  try {
    [allLights, savedTargetIds] = await Promise.all([api("lights"), api("target-lights")]);
    renderTargetLights();
  } catch (e) {
    showToast(e.message, true);
  }
  loadThemes().catch((e) => showToast(e.message, true));
}

init();
