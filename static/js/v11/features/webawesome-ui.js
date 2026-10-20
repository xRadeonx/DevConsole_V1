const WA_JS = "/static/vendor/v11/webawesome.bundle.js";
const ENV_ORDER = ["develop", "test", "main"];

let bootPromise = null;
let refreshTimer = null;

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
  if (envState.map && envState.activity) return "success";
  if (envState.configured) return "warning";
  return "neutral";
}

function compactLabel(env, envState) {
  const short = env === "develop" ? "DEV" : env.toUpperCase();
  if (envState.map && envState.activity) return `${short} · M✓ A✓`;
  if (envState.map) return `${short} · M✓ A!`;
  if (envState.activity) return `${short} · M! A✓`;
  return `${short} · M! A!`;
}

function badgeTooltip(env, envState) {
  if (envState.map && envState.activity) {
    return `${env.toUpperCase()}: Mapa Operativo y Actividad listos`;
  }
  if (envState.configured) {
    const missing = [];
    if (!envState.map) missing.push("Mapa Operativo");
    if (!envState.activity) missing.push("Actividad");
    return `${env.toUpperCase()}: catálogo detectado; falta completar ${missing.join(" y ")}`;
  }
  return `${env.toUpperCase()}: sin catálogo/configuración local`;
}

function ensureStatusHost() {
  const topbarRight = document.querySelector(".topbar-right");
  const topbarSwitcher = document.getElementById("globalEnvSwitcher");
  const anchor = topbarSwitcher || document.getElementById("dcV11EnvSummary") || document.getElementById("mapEnvSelect");
  if (!anchor) return null;

  let host = document.getElementById("dcV11WaEnvStatus");
  if (!host) {
    host = document.createElement("div");
    host.id = "dcV11WaEnvStatus";
    host.className = "dc-v11-wa-status dc-v11-wa-global-health";
    host.setAttribute("aria-label", "Estado de capacidades multi-entorno");
    if (topbarRight && topbarSwitcher) {
      topbarRight.insertBefore(host, topbarSwitcher);
    } else {
      anchor.insertAdjacentElement("afterend", host);
    }
  }
  return host;
}

function renderLoading() {
  const host = ensureStatusHost();
  if (!host) return;
  host.replaceChildren();
  const spinner = document.createElement("wa-spinner");
  spinner.className = "dc-v11-wa-spinner";
  spinner.setAttribute("aria-label", "Actualizando estado de entornos");
  host.appendChild(spinner);
  const label = document.createElement("span");
  label.className = "dc-v11-wa-loading-label";
  label.textContent = "Entornos";
  host.appendChild(label);
}

function renderEnvironmentBadges(state) {
  const host = ensureStatusHost();
  if (!host || !state) return false;
  host.replaceChildren();

  const title = document.createElement("span");
  title.className = "dc-v11-wa-title";
  title.textContent = "READINESS";
  title.title = "Web Awesome · estado vivo de Mapa Operativo (M) y Actividad (A)";
  host.appendChild(title);

  for (const env of ENV_ORDER) {
    const envState = stateFor(state, env);
    const badge = document.createElement("wa-badge");
    const badgeId = `dcV11WaBadge-${env}`;
    badge.id = badgeId;
    badge.setAttribute("variant", badgeVariant(envState));
    badge.setAttribute("appearance", "filled-outlined");
    badge.setAttribute("pill", "");
    badge.textContent = compactLabel(env, envState);
    host.appendChild(badge);

    const tooltip = document.createElement("wa-tooltip");
    tooltip.setAttribute("for", badgeId);
    tooltip.setAttribute("placement", "bottom");
    tooltip.textContent = badgeTooltip(env, envState);
    host.appendChild(tooltip);
  }
  return true;
}

async function refreshStatus({ showLoading = false } = {}) {
  if (showLoading) renderLoading();
  const state = await fetchEnvironmentState();
  if (state) renderEnvironmentBadges(state);
  return state;
}

function scheduleRefresh() {
  window.clearTimeout(refreshTimer);
  refreshTimer = window.setTimeout(() => refreshStatus({ showLoading: true }), 80);
}

async function loadWebAwesome() {
  // Never load Web Awesome's global stylesheet into the legacy document. Its
  // reset/tokens alter V1 buttons, selects and console filters. Components keep
  // their own shadow-DOM styles and DevConsole styles only their host surfaces.
  await loadScript(WA_JS, "webawesome-core");
  await Promise.all([
    customElements.whenDefined("wa-badge"),
    customElements.whenDefined("wa-tooltip"),
    customElements.whenDefined("wa-spinner"),
  ]);
  document.documentElement.dataset.dcWebAwesome = globalThis.DevConsoleWebAwesome?.version || "loaded";
  await refreshStatus({ showLoading: true });
  window.addEventListener("focus", scheduleRefresh);
  document.addEventListener("devconsole:v11-environments-updated", scheduleRefresh);

  // Legacy code rebuilds the topbar environment switcher dynamically. Keep the
  // readiness surface attached without replacing those canonical controls.
  const topbar = document.querySelector(".topbar-right");
  if (topbar) {
    const observer = new MutationObserver(() => {
      if (!document.getElementById("dcV11WaEnvStatus")) scheduleRefresh();
    });
    observer.observe(topbar, { childList: true });
  }
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
