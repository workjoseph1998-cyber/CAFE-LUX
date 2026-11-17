"use strict";
const layout = document.getElementById("admin-layout");
const sidebarToggle = document.getElementById("sidebar-toggle");
function stored(key, fallback) {
  try {
    return localStorage.getItem("lux.admin." + key) || fallback;
  } catch {
    return fallback;
  }
}
function remember(key, value) {
  try {
    localStorage.setItem("lux.admin." + key, value);
  } catch {}
}
function applySidebar(collapsed) {
  layout?.classList.toggle("is-collapsed", collapsed);
  sidebarToggle?.setAttribute("aria-expanded", String(!collapsed));
  sidebarToggle?.setAttribute(
    "title",
    collapsed ? "Expand sidebar" : "Collapse sidebar",
  );
}
applySidebar(stored("sidebar", "expanded") === "collapsed");
sidebarToggle?.addEventListener("click", () => {
  if (matchMedia("(max-width: 720px)").matches) {
    layout.classList.toggle("menu-open");
    sidebarToggle.setAttribute(
      "aria-expanded",
      String(layout.classList.contains("menu-open")),
    );
  } else {
    const collapsed = !layout.classList.contains("is-collapsed");
    applySidebar(collapsed);
    remember("sidebar", collapsed ? "collapsed" : "expanded");
  }
});
const density = document.getElementById("table-density");
function setDensity(value) {
  const selected = value === "comfortable" ? "comfortable" : "compact";
  document.body.dataset.density = selected;
  if (density) density.value = selected;
}
setDensity(stored("density", "compact"));
density?.addEventListener("change", () => {
  setDensity(density.value);
  remember("density", density.value);
});
const rowSelects = [...document.querySelectorAll(".row-select")];
function selection() {
  const n = rowSelects.filter((x) => x.checked).length;
  const counter = document.getElementById("selected-count");
  if (counter) counter.textContent = n + " selected";
  const apply = document.getElementById("bulk-apply");
  if (apply) apply.disabled = n === 0;
}
document.getElementById("select-all")?.addEventListener("change", (e) => {
  rowSelects.forEach((x) => (x.checked = e.target.checked));
  selection();
});
rowSelects.forEach((x) => x.addEventListener("change", selection));
const dirtyForms = new Set();
document.addEventListener("input", (e) => {
  const f = e.target.form;
  if (f?.hasAttribute("data-unsaved")) {
    dirtyForms.add(f);
    const status = document.getElementById("save-state");
    if (status) status.textContent = "Unsaved changes";
  }
});
window.addEventListener("beforeunload", (e) => {
  if (dirtyForms.size) {
    e.preventDefault();
    e.returnValue = "";
  }
});
document.addEventListener("submit", (e) => {
  const message = e.submitter?.dataset.confirm || e.target.dataset.confirm;
  if (message && !confirm(message)) {
    e.preventDefault();
    return;
  }
  if (
    dirtyForms.size > 1 ||
    (dirtyForms.size === 1 && !dirtyForms.has(e.target))
  ) {
    if (
      !confirm(
        "Other forms have unsaved changes. Continue and discard those changes?",
      )
    ) {
      e.preventDefault();
      return;
    }
  }
  dirtyForms.clear();
});
const inspector = document.getElementById("order-inspector");
document
  .getElementById("close-inspector")
  ?.addEventListener("click", () => inspector.close());
document.querySelectorAll("[data-inspect]").forEach((link) =>
  link.addEventListener("click", async (e) => {
    if (!inspector?.showModal) return;
    e.preventDefault();
    try {
      const response = await fetch(link.href, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Unavailable");
      const doc = new DOMParser().parseFromString(
        await response.text(),
        "text/html",
      );
      const detail = doc.querySelector(".order-detail");
      if (!detail) throw new Error("Sign in required");
      document.getElementById("order-panel-content").replaceChildren(detail);
      inspector.showModal();
      document.getElementById("close-inspector").focus();
    } catch {
      location.href = link.href;
    }
  }),
);
inspector?.addEventListener("click", (e) => {
  if (e.target === inspector) inspector.close();
});
const upload = document.querySelector("[name=upload]");
let previewUrl;
upload?.addEventListener("change", () => {
  const preview = document.querySelector(".upload-preview");
  if (!preview) return;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  if (upload.files[0]) {
    previewUrl = URL.createObjectURL(upload.files[0]);
    preview.src = previewUrl;
    preview.hidden = false;
  }
});
document.querySelectorAll('a[href^="#"]').forEach((link) =>
  link.addEventListener("click", () => {
    const section = document.getElementById(link.hash.slice(1));
    if (section?.tagName === "DETAILS") section.open = true;
  }),
);
if (location.hash) {
  const section = document.getElementById(location.hash.slice(1));
  if (section?.tagName === "DETAILS") section.open = true;
}
