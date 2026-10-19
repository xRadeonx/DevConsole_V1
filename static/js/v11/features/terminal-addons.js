const XTERM_JS = "/static/js/xterm.js";
const XTERM_CSS = "/static/css/xterm.css";
const FIT_JS = "/static/vendor/terminal-lab/addon-fit.js";
const SEARCH_JS = "/static/vendor/terminal-lab/addon-search.js";

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

function makeSearchBar(parent, terminal, searchAddon) {
  if (!parent || parent.querySelector(":scope > .dc-v11-terminal-search")) return null;
  const bar = document.createElement("div");
  bar.className = "dc-v11-terminal-search";
  bar.hidden = true;
  bar.innerHTML = `
    <img src="/static/vendor/terminal-lab/icons/search.svg" alt="" aria-hidden="true">
    <input type="search" aria-label="Buscar en terminal" placeholder="Buscar en salida…">
    <button type="button" data-dir="prev" title="Coincidencia anterior">↑</button>
    <button type="button" data-dir="next" title="Coincidencia siguiente">↓</button>
    <button type="button" data-close title="Cerrar búsqueda">×</button>
  `;
  parent.style.position = parent.style.position || "relative";
  parent.appendChild(bar);

  const input = bar.querySelector("input");
  const find = (direction = "next") => {
    const value = input.value;
    if (!value) return;
    const options = {
      caseSensitive: false,
      wholeWord: false,
      regex: false,
      decorations: {
        matchBackground: "#334155",
        matchBorder: "#38bdf8",
        matchOverviewRuler: "#38bdf8",
        activeMatchBackground: "#0ea5e9",
        activeMatchBorder: "#e0f2fe",
        activeMatchColorOverviewRuler: "#e0f2fe",
      },
    };
    if (direction === "prev") searchAddon.findPrevious(value, options);
    else searchAddon.findNext(value, options);
  };

  input.addEventListener("input", () => find("next"));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      find(event.shiftKey ? "prev" : "next");
    } else if (event.key === "Escape") {
      event.preventDefault();
      bar.hidden = true;
      terminal.focus();
    }
  });
  bar.querySelector('[data-dir="prev"]').addEventListener("click", () => find("prev"));
  bar.querySelector('[data-dir="next"]').addEventListener("click", () => find("next"));
  bar.querySelector("[data-close]").addEventListener("click", () => {
    bar.hidden = true;
    terminal.focus();
  });

  return {
    open() {
      bar.hidden = false;
      input.focus();
      input.select();
    },
    close() {
      bar.hidden = true;
    },
  };
}

function promoteTerminalConstructor() {
  const BaseTerminal = globalThis.Terminal;
  const FitCtor = globalThis.FitAddon?.FitAddon;
  const SearchCtor = globalThis.SearchAddon?.SearchAddon;
  if (!BaseTerminal || !FitCtor || !SearchCtor) return false;
  if (BaseTerminal.__dcV11Enhanced) return true;

  class DevConsoleTerminal extends BaseTerminal {
    constructor(options) {
      super(options);
      this.__dcV11Fit = new FitCtor();
      this.__dcV11Search = new SearchCtor();
      this.loadAddon(this.__dcV11Fit);
      this.loadAddon(this.__dcV11Search);
      this.__dcV11SearchUi = null;
      this.__dcV11ResizeObserver = null;

      this.attachCustomKeyEventHandler((event) => {
        const isFind = event.type === "keydown"
          && (event.ctrlKey || event.metaKey)
          && event.key.toLowerCase() === "f";
        if (isFind) {
          event.preventDefault();
          this.__dcV11SearchUi?.open();
          return false;
        }
        return true;
      });
    }

    open(parent) {
      super.open(parent);
      this.__dcV11SearchUi = makeSearchBar(parent, this, this.__dcV11Search);
      const fit = () => {
        try { this.__dcV11Fit.fit(); } catch (_) {}
      };
      requestAnimationFrame(fit);
      if (globalThis.ResizeObserver) {
        this.__dcV11ResizeObserver = new ResizeObserver(() => requestAnimationFrame(fit));
        this.__dcV11ResizeObserver.observe(parent);
      }
    }

    dispose() {
      try { this.__dcV11ResizeObserver?.disconnect(); } catch (_) {}
      this.__dcV11ResizeObserver = null;
      super.dispose();
    }
  }

  DevConsoleTerminal.__dcV11Enhanced = true;
  DevConsoleTerminal.__dcV11Base = BaseTerminal;
  globalThis.Terminal = DevConsoleTerminal;
  return true;
}

async function loadTerminalStack() {
  ensureStyle(XTERM_CSS, "xterm-css");
  if (!globalThis.Terminal) await loadScript(XTERM_JS, "xterm-core");
  if (!globalThis.FitAddon?.FitAddon) await loadScript(FIT_JS, "xterm-fit-addon");
  if (!globalThis.SearchAddon?.SearchAddon) await loadScript(SEARCH_JS, "xterm-search-addon");
  const promoted = promoteTerminalConstructor();
  if (promoted) {
    document.documentElement.dataset.dcXtermAddons = "fit,search";
  }
  return promoted;
}

export function bootTerminalAddons() {
  if (bootPromise) return bootPromise;
  bootPromise = new Promise((resolve) => {
    const start = () => loadTerminalStack().then(resolve).catch((error) => {
      console.warn("[v1.1/terminal] addons unavailable; legacy xterm remains usable", error);
      resolve(false);
    });
    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(start, { timeout: 1800 });
    } else {
      window.setTimeout(start, 600);
    }
  });
  return bootPromise;
}
