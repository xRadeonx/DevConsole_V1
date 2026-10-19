const WA_JS = "/static/vendor/v11/webawesome.bundle.js";
const WA_CSS = "/static/vendor/v11/webawesome.css";
const ENV_ORDER = ["develop", "test", "main"];

let bootPromise = null;

function ensureStyle(href, marker) {
  if (document.querySelector(`link[data-devconsole-v11="${marker}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  link.dataset.devconsoleV11 = marker;
  document.head.appendChild(link);
}

function loadScript(src, marker) {
  const existing = document.querySelector(`script[data-devconsole-v11="${marker}"]`);
  if (existing) {
    if (existing.dataset.loaded === "true") return Promise.resolve();
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", resolve, { once: true });
      existing.addEventListener("error", reject, { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.dataset.devconsoleV11 = marker;
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      resolve();
    }, { once: true });
    script.addEventListener("error", () => reject(new Error(`No se pudo cargar ${src}`)), { once: true });
    document.head.appendChild(script);
  });
}

async function fetchEnvironmentState() {
  try {
    const response = await fetch("/api/v1.1/environments", { cache: "no-store" });
    if (!response.ok) return null;
    return await response.json();
  } catch (_) {
    return null;
  }
}

function stateFor(state, env) {
  return state?.environments?.[env] || {};
}

function badgeVariant(envState) {
  if (envState.map_ready && envState.activity_ready) return "success";
  if (envState.configured) return "warning";
  return "neutral";
}

function badgeTooltip(env, envState) {
  if (envState.map_ready && envState.activity_ready) {
    return `${env.toUpperCase()}: Mapa y Actividad listos`;
  }
  if (envState.configured) {
    const missing = [];
    if (!envState.map_ready) missing.push("Mapa");
    if (!envState.activity_ready) missing.push("Actividad");
    return `${env.toUpperCase()}: catálogo detectado; falta completar ${missing.join(" y ")}`;
  }
  return `${env.toUpperCase()}: sin catálogo/configuración local`;
}

function ensureStatusHost() {
  const anchor = document.getElementById("dcV11EnvSummary") || document.getElementById("mapEnvSelect");
  if (!anchor) return null;
  let host = document.getElementById("dcV11WaEnvStatus");
  if (!host) {
    host = document.createElement("span");
    host.id = "dcV11WaEnvStatus";
    host.className = "dc-v11-wa-status";
    anchor.insertAdjacentElement("afterend", host);
  }
  return host;
}

function renderEnvironmentBadges(state) {
  const host = ensureStatusHost();
  if (!host || !state) return false;
  host.replaceChildren();

  for (const env of ENV_ORDER) {
    const envState = stateFor(state, env);
    const badge = document.createElement("wa-badge");
    const badgeId = `dcV11WaBadge-${env}`;
    badge.id = badgeId;
    badge.setAttribute("variant", badgeVariant(envState));
    badge.setAttribute("appearance", "filled-outlined");
    badge.setAttribute("pill", "");
    badge.textContent = env.toUpperCase();
    host.appendChild(badge);

    const tooltip = document.createElement("wa-tooltip");
    tooltip.setAttribute("for", badgeId);
    tooltip.setAttribute("placement", "bottom");
    tooltip.textContent = badgeTooltip(env, envState);
    host.appendChild(tooltip);
  }
  return true;
}

async function refreshStatus() {
  const state = await fetchEnvironmentState();
  if (state) renderEnvironmentBadges(state);
  return state;
}

async function loadWebAwesome() {
  ensureStyle(WA_CSS, "webawesome-css");
  await loadScript(WA_JS, "webawesome-core");
  await Promise.all([
    customElements.whenDefined("wa-badge"),
    customElements.whenDefined("wa-tooltip"),
  ]);
  document.documentElement.dataset.dcWebAwesome = globalThis.DevConsoleWebAwesome?.version || "loaded";
  await refreshStatus();
  window.addEventListener("focus", refreshStatus);
  document.addEventListener("devconsole:v11-environments-updated", refreshStatus);
  return true;
}

export function bootWebAwesomeUi() {
  if (bootPromise) return bootPromise;
  bootPromise = loadWebAwesome().catch((error) => {
    console.warn("[v1.1/webawesome] unavailable; legacy controls remain active", error);
    return false;
  });
  return bootPromise;
}
