const SPLIT_JS = "/static/vendor/v11/split.min.js";
const MAP_SIZES_KEY = "devconsole.v11.map.split";

let loadPromise = null;
let mapSplit = null;
let media = null;

function loadSplit() {
  if (typeof globalThis.Split === "function") return Promise.resolve(globalThis.Split);
  if (loadPromise) return loadPromise;
  loadPromise = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = SPLIT_JS;
    script.async = true;
    script.dataset.devconsoleV11 = "splitjs";
    script.addEventListener("load", () => resolve(typeof globalThis.Split === "function" ? globalThis.Split : null), { once: true });
    script.addEventListener("error", () => resolve(null), { once: true });
    document.head.appendChild(script);
  });
  return loadPromise;
}

function savedSizes() {
  try {
    const value = JSON.parse(localStorage.getItem(MAP_SIZES_KEY) || "null");
    if (Array.isArray(value) && value.length === 2 && value.every((item) => Number.isFinite(Number(item)))) {
      return value.map(Number);
    }
  } catch (_) {}
  return [42, 58];
}

function destroyMapSplit() {
  if (mapSplit?.destroy) {
    try { mapSplit.destroy(); } catch (_) {}
  }
  mapSplit = null;
  const layout = document.querySelector(".map-grid-layout");
  if (layout) layout.classList.remove("dc-v11-map-split");
}

async function mountMapSplit() {
  const layout = document.querySelector(".map-grid-layout");
  const left = layout?.querySelector(".map-tactical-panel");
  const right = layout?.querySelector(".zone-detail-panel");
  if (!layout || !left || !right || !media?.matches) {
    destroyMapSplit();
    return;
  }
  if (mapSplit) return;

  const Split = await loadSplit();
  if (!Split || !media?.matches || !document.body.contains(layout)) return;

  layout.classList.add("dc-v11-map-split");
  mapSplit = Split([left, right], {
    sizes: savedSizes(),
    minSize: [300, 360],
    gutterSize: 9,
    snapOffset: 18,
    cursor: "col-resize",
    onDragEnd(sizes) {
      try { localStorage.setItem(MAP_SIZES_KEY, JSON.stringify(sizes)); } catch (_) {}
      window.dispatchEvent(new Event("resize"));
    },
  });
  document.documentElement.dataset.dcSplit = "1.6.5";
}

export function bootSplitLayouts() {
  media = window.matchMedia("(min-width: 1100px)");
  const refresh = () => {
    if (media.matches) mountMapSplit();
    else destroyMapSplit();
  };

  refresh();
  media.addEventListener?.("change", refresh);

  // The map is a normal tab and can be rendered after bootstrap. Observe only
  // until the canonical layout appears; Split.js then owns just its gutter.
  if (!document.querySelector(".map-grid-layout")) {
    const observer = new MutationObserver(() => {
      if (document.querySelector(".map-grid-layout")) {
        observer.disconnect();
        refresh();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => observer.disconnect(), 10000);
  }
}
