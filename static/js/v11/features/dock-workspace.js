const DOCKVIEW_JS = "/static/vendor/terminal-lab/dockview.js";
const DOCKVIEW_CSS = "/static/vendor/terminal-lab/dockview.css";
const LAYOUT_KEY = "devconsole.v11.dockview.layout";
const MAX_INITIAL_PANELS = 6;

let loadPromise = null;
let overlay = null;
let dockApi = null;
let pollTimer = null;
let visible = false;
const panelViews = new Map();

function ensureStyle(href) {
  if (document.querySelector('link[data-devconsole-v11="dockview-css"]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  link.dataset.devconsoleV11 = "dockview-css";
  document.head.appendChild(link);
}

function loadDockview() {
  if (globalThis.dockview?.createDockview) return Promise.resolve(globalThis.dockview);
  if (loadPromise) return loadPromise;

  ensureStyle(DOCKVIEW_CSS);
  loadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-devconsole-v11="dockview"]');
    if (existing) {
      if (globalThis.dockview?.createDockview) {
        resolve(globalThis.dockview);
        return;
      }
      existing.addEventListener("load", () => resolve(globalThis.dockview), { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = DOCKVIEW_JS;
    script.async = true;
    script.dataset.devconsoleV11 = "dockview";
    script.addEventListener("load", () => {
      if (!globalThis.dockview?.createDockview) {
        reject(new Error("Dockview cargó sin exponer createDockview"));
        return;
      }
      document.documentElement.dataset.dcDockview = "8.5.1";
      resolve(globalThis.dockview);
    }, { once: true });
    script.addEventListener("error", () => reject(new Error("No se pudo cargar Dockview local")), { once: true });
    document.head.appendChild(script);
  });
  return loadPromise;
}

function statusClass(status) {
  const value = String(status || "STOPPED").toUpperCase();
  if (value === "RUNNING") return "is-running";
  if (value === "FAILED") return "is-error";
  if (value === "STANDBY") return "is-standby";
  if (value === "STARTING") return "is-starting";
  return "is-stopped";
}

class ServiceLogPanel {
  constructor() {
    this.service = "";
    this.element = document.createElement("section");
    this.element.className = "dc-v11-dock-panel";

    this.meta = document.createElement("div");
    this.meta.className = "dc-v11-dock-panel-meta";

    this.status = document.createElement("span");
    this.status.className = "dc-v11-dock-status is-stopped";
    this.status.textContent = "DETENIDO";

    this.runtime = document.createElement("span");
    this.runtime.className = "dc-v11-dock-runtime";
    this.runtime.textContent = "sin runtime";

    this.meta.append(this.status, this.runtime);

    this.pre = document.createElement("pre");
    this.pre.className = "dc-v11-dock-log";
    this.pre.textContent = "Esperando salida…";

    this.element.append(this.meta, this.pre);
  }

  init(params) {
    this.service = String(params?.params?.service || params?.api?.id || "");
    if (this.service) panelViews.set(this.service, this);
  }

  update(item) {
    const state = String(item?.status || "STOPPED").toUpperCase();
    this.status.className = `dc-v11-dock-status ${statusClass(state)}`;
    this.status.textContent = state;

    const runtime = item?.runtime_host && item.runtime_host !== "none" ? item.runtime_host : "sin runtime";
    const port = Number(item?.port || 0);
    const pid = item?.pid ? ` · PID ${item.pid}` : "";
    this.runtime.textContent = `${runtime}${port ? ` · :${port}` : ""}${pid}`;

    const lines = Array.isArray(item?.recent_lines) ? item.recent_lines : [];
    if (lines.length) {
      this.pre.textContent = lines.join("\n");
      this.pre.scrollTop = this.pre.scrollHeight;
    } else if (item?.recent_error) {
      this.pre.textContent = String(item.recent_error);
    } else {
      this.pre.textContent = state === "STOPPED" ? "Servicio detenido · sin salida reciente" : "Sin salida reciente";
    }
  }

  dispose() {
    if (this.service && panelViews.get(this.service) === this) panelViews.delete(this.service);
  }
}

async function fetchMosaic(maxLines = 120) {
  const response = await fetch(`/api/services/mosaic?max_lines=${maxLines}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = await response.json();
  return Array.isArray(payload?.services) ? payload.services : [];
}

function updateViews(items) {
  const byName = new Map(items.map((item) => [String(item.name), item]));
  for (const [service, view] of panelViews) {
    const item = byName.get(service);
    if (item) view.update(item);
  }
  const badge = document.getElementById("dcV11DockLiveBadge");
  if (badge) {
    const running = items.filter((item) => String(item.status).toUpperCase() === "RUNNING").length;
    badge.textContent = `${running}/${items.length} activos`;
  }
}

async function refreshPanels() {
  if (!visible) return;
  try {
    updateViews(await fetchMosaic(120));
  } catch (error) {
    const badge = document.getElementById("dcV11DockLiveBadge");
    if (badge) badge.textContent = "sin conexión";
    console.debug("[v1.1/dock] no se pudo actualizar el mosaico", error);
  }
}

function startPolling() {
  stopPolling();
  refreshPanels();
  pollTimer = window.setInterval(refreshPanels, 2200);
}

function stopPolling() {
  if (pollTimer) window.clearInterval(pollTimer);
  pollTimer = null;
}

function saveLayout() {
  if (!dockApi?.toJSON) return;
  try {
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(dockApi.toJSON()));
  } catch (_) {
    // Layout persistence is convenience-only.
  }
}

function restoreLayout() {
  if (!dockApi?.fromJSON) return false;
  try {
    const raw = localStorage.getItem(LAYOUT_KEY);
    if (!raw) return false;
    dockApi.fromJSON(JSON.parse(raw));
    return true;
  } catch (error) {
    console.debug("[v1.1/dock] layout guardado inválido; se regenerará", error);
    try { localStorage.removeItem(LAYOUT_KEY); } catch (_) {}
    return false;
  }
}

function safeId(name) {
  return `svc-${String(name).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

async function seedPanels() {
  const items = await fetchMosaic(80);
  const ranked = [...items].sort((a, b) => {
    const ar = String(a.status).toUpperCase() === "RUNNING" ? 0 : 1;
    const br = String(b.status).toUpperCase() === "RUNNING" ? 0 : 1;
    return ar - br || String(a.name).localeCompare(String(b.name));
  });
  const selected = ranked.slice(0, MAX_INITIAL_PANELS);
  let previousId = null;

  selected.forEach((item, index) => {
    const id = safeId(item.name);
    const options = {
      id,
      component: "service-log",
      title: String(item.name),
      params: { service: String(item.name) },
    };
    if (previousId) {
      options.position = {
        referencePanel: previousId,
        direction: index % 2 === 1 ? "right" : "below",
      };
    }
    dockApi.addPanel(options);
    previousId = id;
  });

  updateViews(items);
}

function buildOverlay() {
  if (overlay) return overlay;
  overlay = document.createElement("div");
  overlay.id = "dcV11DockOverlay";
  overlay.className = "dc-v11-dock-overlay";
  overlay.hidden = true;
  overlay.innerHTML = `
    <div class="dc-v11-dock-shell" role="dialog" aria-modal="true" aria-label="Consolas en modo IDE">
      <header class="dc-v11-dock-header">
        <div>
          <strong>Consolas · Modo IDE</strong>
          <span>Dockview 8.5.1 · arrastra pestañas y paneles</span>
        </div>
        <div class="dc-v11-dock-actions">
          <span id="dcV11DockLiveBadge" class="dc-v11-dock-live">cargando…</span>
          <button type="button" data-dock-reset>Reiniciar layout</button>
          <button type="button" data-dock-close aria-label="Cerrar modo IDE">×</button>
        </div>
      </header>
      <div id="dcV11DockHost" class="dc-v11-dock-host"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector("[data-dock-close]").addEventListener("click", closeDockWorkspace);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeDockWorkspace();
  });
  overlay.querySelector("[data-dock-reset]").addEventListener("click", async () => {
    try { localStorage.removeItem(LAYOUT_KEY); } catch (_) {}
    if (dockApi?.dispose) dockApi.dispose();
    dockApi = null;
    panelViews.clear();
    const host = document.getElementById("dcV11DockHost");
    if (host) host.replaceChildren();
    await initializeDockview(true);
  });
  return overlay;
}

async function initializeDockview(forceSeed = false) {
  if (dockApi) return dockApi;
  const lib = await loadDockview();
  const host = document.getElementById("dcV11DockHost");
  if (!host) throw new Error("Contenedor Dockview no disponible");

  dockApi = lib.createDockview(host, {
    createComponent: () => new ServiceLogPanel(),
  });

  let restored = false;
  if (!forceSeed) restored = restoreLayout();
  if (!restored) await seedPanels();
  return dockApi;
}

async function openDockWorkspace() {
  const root = buildOverlay();
  root.hidden = false;
  visible = true;
  document.body.classList.add("dc-v11-dock-open");

  const badge = document.getElementById("dcV11DockLiveBadge");
  if (badge) badge.textContent = "cargando…";

  try {
    await initializeDockview(false);
    startPolling();
  } catch (error) {
    console.warn("[v1.1/dock] Dockview no disponible; el muro clásico sigue intacto", error);
    if (badge) badge.textContent = "Dockview no disponible";
  }
}

function closeDockWorkspace() {
  if (!overlay) return;
  saveLayout();
  visible = false;
  stopPolling();
  overlay.hidden = true;
  document.body.classList.remove("dc-v11-dock-open");
}

function installLauncher() {
  const toolbar = document.getElementById("consoleWallToolbar");
  if (!toolbar || document.getElementById("btnV11DockWorkspace")) return false;

  const button = document.createElement("button");
  button.type = "button";
  button.id = "btnV11DockWorkspace";
  button.className = "cw-btn dc-v11-dock-launcher";
  button.textContent = "▦ Modo IDE";
  button.title = "Abrir las consolas en Dockview: paneles acoplables y layout persistente";
  button.addEventListener("click", openDockWorkspace);

  const spacer = toolbar.querySelector(".cw-spacer");
  toolbar.insertBefore(button, spacer || toolbar.firstChild);
  return true;
}

export function bootDockWorkspace() {
  const installed = installLauncher();
  if (!installed) {
    const observer = new MutationObserver(() => {
      if (installLauncher()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => observer.disconnect(), 8000);
  }

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && visible) closeDockWorkspace();
  });
}
