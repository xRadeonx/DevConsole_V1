const GRID_JS = "/static/vendor/v11/gridjs.umd.js";
const GRID_CSS = "/static/vendor/v11/gridjs-mermaid.min.css";

let loadPromise = null;
const instances = new Map();

function ensureCss() {
  if (document.querySelector('link[data-devconsole-v11="gridjs-css"]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = GRID_CSS;
  link.dataset.devconsoleV11 = "gridjs-css";
  document.head.appendChild(link);
}

function loadGrid() {
  if (globalThis.gridjs?.Grid) return Promise.resolve(globalThis.gridjs);
  if (loadPromise) return loadPromise;
  ensureCss();
  loadPromise = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = GRID_JS;
    script.async = true;
    script.dataset.devconsoleV11 = "gridjs";
    script.addEventListener("load", () => resolve(globalThis.gridjs?.Grid ? globalThis.gridjs : null), { once: true });
    script.addEventListener("error", () => resolve(null), { once: true });
    document.head.appendChild(script);
  });
  return loadPromise;
}

function tableSnapshot(table, lib) {
  const headers = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim());
  const rows = [...table.querySelectorAll("tbody tr")]
    .filter((row) => !row.querySelector("td[colspan]"))
    .map((row) => [...row.children].map((cell) => lib.html(cell.innerHTML)));
  return { headers, rows };
}

function language() {
  return {
    search: { placeholder: "Buscar en la tabla…" },
    pagination: {
      previous: "Anterior",
      next: "Siguiente",
      showing: "Mostrando",
      results: () => "registros",
    },
    noRecordsFound: "Sin registros para mostrar",
    error: "No fue posible cargar la tabla",
  };
}

async function enhanceTable(table, { pagination = false } = {}) {
  if (!table || table.dataset.dcGrid === "true") return;
  const lib = await loadGrid();
  if (!lib || !document.body.contains(table) || table.dataset.dcGrid === "true") return;

  const host = document.createElement("div");
  host.className = "dc-v11-grid-host";
  table.insertAdjacentElement("afterend", host);

  const render = () => {
    const { headers, rows } = tableSnapshot(table, lib);
    const grid = instances.get(table);
    const config = {
      columns: headers,
      data: rows,
      search: true,
      sort: true,
      language: language(),
      pagination: pagination ? { limit: 25, summary: true } : false,
      className: {
        table: "dc-v11-grid-table",
        search: "dc-v11-grid-search",
      },
    };
    if (grid) {
      grid.updateConfig(config).forceRender();
    } else {
      const created = new lib.Grid(config);
      instances.set(table, created);
      created.render(host);
      table.dataset.dcGrid = "true";
      table.classList.add("dc-v11-grid-source");
      document.documentElement.dataset.dcGridjs = "6.2.0";
    }
  };

  render();
  const tbody = table.tBodies?.[0];
  if (tbody) {
    let timer = null;
    const observer = new MutationObserver(() => {
      window.clearTimeout(timer);
      timer = window.setTimeout(render, 80);
    });
    observer.observe(tbody, { childList: true, subtree: true, characterData: true, attributes: true });
  }
}

function restoreWorkspaceLegacyTable() {
  const workspace = document.getElementById("workspaceTableBody")?.closest("table");
  if (!workspace) return;
  workspace.classList.remove("dc-v11-grid-source");
  workspace.removeAttribute("data-dc-grid");
  const next = workspace.nextElementSibling;
  if (next?.classList?.contains("dc-v11-grid-host")) next.remove();
}

function discoverTables() {
  // Workspace already has purpose-built controls/actions whose layout is more
  // useful than a generic data-grid. Preserve it exactly as V1 renders it.
  restoreWorkspaceLegacyTable();

  // Grid.js is valuable in Activity because that view is genuinely tabular and
  // benefits from search/sort/pagination without replacing its data source.
  const activity = document.getElementById("activityTable");
  if (activity) enhanceTable(activity, { pagination: true });
}

export function bootGridEnhancements() {
  discoverTables();
  const observer = new MutationObserver(() => {
    discoverTables();
    if (document.getElementById("activityTable")?.dataset.dcGrid === "true") {
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  window.setTimeout(() => observer.disconnect(), 12000);
}
