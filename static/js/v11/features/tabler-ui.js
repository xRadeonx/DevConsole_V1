const TABLER_CSS = "/static/vendor/v11/tabler.min.css";
const TABLER_JS = "/static/vendor/v11/tabler.min.js";
const TABLER_ADAPTER_CSS = "/static/css/v11-tabler.css";
const TABLER_ICONS = "/static/vendor/v11/tabler-icons.svg";
const DISABLE_KEY = "devconsole.v11.tabler.disabled";

let bootPromise = null;
let observer = null;
let themeObserver = null;

const NAV_ICONS = Object.freeze({
  services: "layout-dashboard",
  consoles: "terminal-2",
  workspace: "git-branch",
  k8s: "brand-kubernetes",
  site: "settings",
  deployments: "rocket",
  activity: "activity",
  infra: "server-2",
  map: "map-2",
  sessions: "users",
  security: "shield-lock",
  database: "database",
  config: "settings-2",
});

function tablerDisabled() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("tabler") === "off" || params.get("ui") === "legacy") return true;
  try {
    return localStorage.getItem(DISABLE_KEY) === "1";
  } catch (_) {
    return false;
  }
}

function ensureStyle(href, marker) {
  const existing = document.querySelector(`link[data-devconsole-tabler="${marker}"]`);
  if (existing) return Promise.resolve(existing);
  return new Promise((resolve) => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.dataset.devconsoleTabler = marker;
    link.addEventListener("load", () => resolve(link), { once: true });
    link.addEventListener("error", () => resolve(null), { once: true });
    document.head.appendChild(link);
  });
}

function ensureScript(src, marker) {
  const existing = document.querySelector(`script[data-devconsole-tabler="${marker}"]`);
  if (existing) {
    if (existing.dataset.loaded === "true") return Promise.resolve(existing);
    return new Promise((resolve) => {
      existing.addEventListener("load", () => resolve(existing), { once: true });
      existing.addEventListener("error", () => resolve(null), { once: true });
    });
  }
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.dataset.devconsoleTabler = marker;
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      resolve(script);
    }, { once: true });
    script.addEventListener("error", () => resolve(null), { once: true });
    document.head.appendChild(script);
  });
}

function iconElement(name, className = "dc-tabler-icon") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.classList.add(...className.split(/\s+/).filter(Boolean));
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `${TABLER_ICONS}#tabler-${name}`);
  svg.appendChild(use);
  return svg;
}

function syncTheme() {
  const theme = String(document.documentElement.dataset.theme || "").toLowerCase();
  document.documentElement.setAttribute("data-bs-theme", theme === "light" ? "light" : "dark");
}

function decorateShell() {
  const topbar = document.getElementById("topbar");
  topbar?.classList.add("navbar", "navbar-expand-md", "dc-tabler-topbar");
  document.querySelector(".topbar-brand")?.classList.add("navbar-brand");

  const toggle = document.getElementById("sidebarToggleBtn");
  toggle?.classList.add("btn", "btn-icon", "btn-ghost-secondary", "dc-tabler-sidebar-toggle");
  if (toggle && !toggle.dataset.dcTablerIcon) {
    toggle.replaceChildren(iconElement("menu-2"));
    toggle.dataset.dcTablerIcon = "true";
  }

  document.getElementById("baseDirPathBtn")?.classList.add("btn", "btn-sm", "btn-outline-secondary", "dc-tabler-path");

  const sidebar = document.getElementById("sidebarNav");
  sidebar?.classList.add("navbar", "navbar-vertical", "navbar-expand-lg", "dc-tabler-sidebar");
  const nav = sidebar?.querySelector(".sidebar-nav");
  nav?.classList.add("navbar-nav");

  for (const item of sidebar?.querySelectorAll(".sidebar-nav-item") || []) {
    item.classList.add("nav-link");
    const label = item.querySelector(".sidebar-nav-label");
    label?.classList.add("nav-link-title");
    const iconHost = item.querySelector(".sidebar-nav-icon");
    iconHost?.classList.add("nav-link-icon");
    const name = NAV_ICONS[item.dataset.tab] || "circle";
    if (iconHost && iconHost.dataset.dcTablerIcon !== name) {
      iconHost.replaceChildren(iconElement(name));
      iconHost.dataset.dcTablerIcon = name;
    }
  }

  for (const label of sidebar?.querySelectorAll(".sidebar-section-label") || []) {
    label.classList.add("dc-tabler-nav-caption");
  }

  document.querySelector(".main-content")?.classList.add("dc-tabler-main");
}

function decorateButtons(root = document) {
  for (const button of root.querySelectorAll?.(".btn") || []) {
    if (button.classList.contains("btn-outline")) button.classList.add("btn-outline-secondary");
    if (button.classList.contains("btn-hero")) button.classList.add("btn-primary");
    if (button.classList.contains("btn-dev")) button.classList.add("btn-warning");
    if (button.classList.contains("btn-test")) button.classList.add("btn-info");
    if (button.classList.contains("btn-main")) button.classList.add("btn-success");
  }

  for (const button of root.querySelectorAll?.(".view-toggle-btn") || []) {
    button.classList.add("btn", "btn-sm", "btn-ghost-secondary");
  }
  for (const button of root.querySelectorAll?.(".sidebar-footer-btn, .sidebar-footer-role") || []) {
    button.classList.add("btn", "btn-ghost-secondary");
  }
  for (const button of root.querySelectorAll?.(".env-btn") || []) {
    button.classList.add("btn", "btn-sm");
  }
}

function decorateForms(root = document) {
  for (const input of root.querySelectorAll?.(
    ".search-input, .filter-card input[type='text'], .filter-card input[type='search'], .modal-overlay input[type='text'], .modal-overlay input[type='search'], .modal-overlay input[type='password']"
  ) || []) {
    if (!input.closest("#tab-consoles")) input.classList.add("form-control", "form-control-sm");
  }

  for (const select of root.querySelectorAll?.(".main-content select, .modal-overlay select") || []) {
    if (!select.closest("#tab-consoles")) select.classList.add("form-select", "form-select-sm");
  }

  for (const checkbox of root.querySelectorAll?.(".main-content input[type='checkbox'], .modal-overlay input[type='checkbox']") || []) {
    if (!checkbox.closest("#tab-consoles")) checkbox.classList.add("form-check-input");
  }
}

function decorateCardsAndTables(root = document) {
  for (const card of root.querySelectorAll?.(
    ".table-card, .filter-card, .service-card, .stat-card, .panel-card, .infra-card, .activity-card"
  ) || []) {
    card.classList.add("card", "dc-tabler-card");
  }

  for (const table of root.querySelectorAll?.(".main-content table") || []) {
    if (table.closest("#tab-consoles")) continue;
    table.classList.add("table", "table-vcenter", "table-hover", "dc-tabler-table");
  }

  for (const modal of root.querySelectorAll?.(".modal-overlay > .modal") || []) {
    modal.classList.add("dc-tabler-modal", "card");
  }

  for (const badge of root.querySelectorAll?.(".chip, .badge-pill, .status-badge") || []) {
    badge.classList.add("badge", "dc-tabler-badge");
  }
}

function decorateKpisAndEnvironment() {
  document.getElementById("kpiRibbon")?.classList.add("dc-tabler-kpi-strip");
  for (const item of document.querySelectorAll(".kpi-item")) item.classList.add("dc-tabler-kpi");
  document.getElementById("globalEnvSwitcher")?.classList.add("btn-group", "dc-tabler-env-switcher");
}

function decorateDynamic(root = document) {
  decorateButtons(root);
  decorateForms(root);
  decorateCardsAndTables(root);
  decorateKpisAndEnvironment();
}

function installObserver() {
  if (observer) return;
  let timer = null;
  observer = new MutationObserver((mutations) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) decorateDynamic(node);
        }
      }
      decorateShell();
      decorateDynamic(document);
    }, 70);
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

function exposeControlApi() {
  if (window.DevConsoleTabler) return;
  Object.defineProperty(window, "DevConsoleTabler", {
    configurable: false,
    enumerable: false,
    writable: false,
    value: Object.freeze({
      active: true,
      disable() {
        try { localStorage.setItem(DISABLE_KEY, "1"); } catch (_) {}
        window.location.reload();
      },
      enable() {
        try { localStorage.removeItem(DISABLE_KEY); } catch (_) {}
        window.location.reload();
      },
    }),
  });
}

async function startTabler() {
  if (tablerDisabled()) {
    document.documentElement.dataset.dcTabler = "disabled";
    return false;
  }

  document.body.classList.add("dc-tabler-ui");
  document.documentElement.dataset.dcTabler = "1.6.1";
  syncTheme();

  // Order matters: Tabler core first, DevConsole compatibility/adaptation last.
  const coreStyle = ensureStyle(TABLER_CSS, "core");
  const adapterStyle = ensureStyle(TABLER_ADAPTER_CSS, "adapter");
  const script = ensureScript(TABLER_JS, "core-js");

  decorateShell();
  decorateDynamic(document);
  installObserver();
  exposeControlApi();

  if (!themeObserver) {
    themeObserver = new MutationObserver(syncTheme);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  await Promise.all([coreStyle, adapterStyle, script]);
  document.dispatchEvent(new CustomEvent("devconsole:tabler-ready", { detail: { version: "1.6.1" } }));
  return true;
}

export function bootTablerUi() {
  if (bootPromise) return bootPromise;
  bootPromise = startTabler().catch((error) => {
    console.warn("[v1.1/tabler] no disponible; se conserva la UI legacy", error);
    document.body.classList.remove("dc-tabler-ui");
    document.documentElement.dataset.dcTabler = "fallback";
    return false;
  });
  return bootPromise;
}
