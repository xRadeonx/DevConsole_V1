const XTERM_JS = "/static/js/xterm.js";
const XTERM_CSS = "/static/css/xterm.css";
const FIT_JS = "/static/vendor/terminal-lab/addon-fit.js";
const SEARCH_JS = "/static/vendor/terminal-lab/addon-search.js";
const WEB_LINKS_JS = "/static/vendor/v11/xterm-web-links.bundle.js";
const WEBGL_JS = "/static/vendor/v11/xterm-webgl.bundle.js";

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
    <span class="dc-v11-terminal-search-label">Buscar en salida</span>
    <input type="search" aria-label="Buscar en terminal" placeholder="texto, error, URL…">
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

function makeTerminalToolbar(parent, terminal, fit, searchUi, renderer, linksEnabled) {
  if (!parent || parent.querySelector(":scope > .dc-v11-terminal-toolbar")) return null;
  const bar = document.createElement("div");
  bar.className = "dc-v11-terminal-toolbar";
  bar.innerHTML = `
    <span class="dc-v11-terminal-toolbar-brand" title="xterm.js con addons V1.1">xterm+</span>
    <button type="button" data-action="find" title="Buscar en la salida (Ctrl+F)">⌕ Buscar</button>
    <button type="button" data-action="fit" title="Ajustar terminal al panel">↔ Ajustar</button>
    <span class="dc-v11-terminal-toolbar-state" data-role="renderer">${renderer.toUpperCase()}</span>
    <span class="dc-v11-terminal-toolbar-state${linksEnabled ? " is-on" : ""}" title="WebLinksAddon: URLs http/https clicables">LINKS</span>
  `;
  parent.appendChild(bar);
  bar.querySelector('[data-action="find"]').addEventListener("click", () => searchUi?.open());
  bar.querySelector('[data-action="fit"]').addEventListener("click", () => {
    try { fit.fit(); } catch (_) {}
    terminal.focus();
  });
  return {
    setRenderer(next) {
      const badge = bar.querySelector('[data-role="renderer"]');
      if (badge) badge.textContent = String(next || "canvas").toUpperCase();
    },
    remove() {
      bar.remove();
    },
  };
}

function openSafeWebLink(_event, uri) {
  try {
    const url = new URL(uri, window.location.href);
    if (url.protocol !== "http:" && url.protocol !== "https:") return;
    const opened = window.open(url.href, "_blank", "noopener,noreferrer");
    if (opened) opened.opener = null;
  } catch (_) {
    // Malformed output must never affect the terminal session.
  }
}

function promoteTerminalConstructor() {
  const BaseTerminal = globalThis.Terminal;
  const FitCtor = globalThis.FitAddon?.FitAddon;
  const SearchCtor = globalThis.SearchAddon?.SearchAddon;
  const WebLinksCtor = globalThis.WebLinksAddon?.WebLinksAddon;
  const WebglCtor = globalThis.WebglAddon?.WebglAddon;
  if (!BaseTerminal || !FitCtor || !SearchCtor) return false;
  if (BaseTerminal.__dcV11Enhanced) return true;

  class DevConsoleTerminal extends BaseTerminal {
    constructor(options) {
      super(options);
      this.__dcV11Fit = new FitCtor();
      this.__dcV11Search = new SearchCtor();
      this.__dcV11Links = null;
      this.__dcV11Webgl = null;
      this.__dcV11SearchUi = null;
      this.__dcV11Toolbar = null;
      this.__dcV11ResizeObserver = null;
      this.loadAddon(this.__dcV11Fit);
      this.loadAddon(this.__dcV11Search);

      if (WebLinksCtor) {
        try {
          this.__dcV11Links = new WebLinksCtor(openSafeWebLink, undefined, true);
          this.loadAddon(this.__dcV11Links);
        } catch (error) {
          console.debug("[v1.1/terminal] WebLinksAddon fallback", error);
          this.__dcV11Links = null;
        }
      }

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
      let renderer = "canvas";

      if (WebglCtor && !this.__dcV11Webgl) {
        try {
          const webgl = new WebglCtor(false);
          this.loadAddon(webgl);
          this.__dcV11Webgl = webgl;
          renderer = "webgl";
          document.documentElement.dataset.dcXtermRenderer = "webgl";
          if (typeof webgl.onContextLoss === "function") {
            webgl.onContextLoss(() => {
              try { webgl.dispose(); } catch (_) {}
              this.__dcV11Webgl = null;
              document.documentElement.dataset.dcXtermRenderer = "canvas";
              this.__dcV11Toolbar?.setRenderer("canvas");
            });
          }
        } catch (error) {
          console.debug("[v1.1/terminal] WebGL no disponible; se mantiene canvas", error);
          this.__dcV11Webgl = null;
          document.documentElement.dataset.dcXtermRenderer = "canvas";
        }
      }

      this.__dcV11Toolbar = makeTerminalToolbar(
        parent,
        this,
        this.__dcV11Fit,
        this.__dcV11SearchUi,
        renderer,
        Boolean(this.__dcV11Links),
      );

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
      try { this.__dcV11Webgl?.dispose(); } catch (_) {}
      try { this.__dcV11Toolbar?.remove(); } catch (_) {}
      this.__dcV11ResizeObserver = null;
      this.__dcV11Webgl = null;
      this.__dcV11Toolbar = null;
      super.dispose();
    }
  }

  DevConsoleTerminal.__dcV11Enhanced = true;
  DevConsoleTerminal.__dcV11Base = BaseTerminal;
  globalThis.Terminal = DevConsoleTerminal;
  return true;
}

async function loadOptionalAddon(src, marker, isReady) {
  if (isReady()) return true;
  try {
    await loadScript(src, marker);
    return isReady();
  } catch (error) {
    console.debug(`[v1.1/terminal] optional addon unavailable: ${marker}`, error);
    return false;
  }
}

async function loadTerminalStack() {
  ensureStyle(XTERM_CSS, "xterm-css");
  if (!globalThis.Terminal) await loadScript(XTERM_JS, "xterm-core");
  if (!globalThis.FitAddon?.FitAddon) await loadScript(FIT_JS, "xterm-fit-addon");
  if (!globalThis.SearchAddon?.SearchAddon) await loadScript(SEARCH_JS, "xterm-search-addon");

  const [linksReady, webglReady] = await Promise.all([
    loadOptionalAddon(WEB_LINKS_JS, "xterm-web-links-addon", () => Boolean(globalThis.WebLinksAddon?.WebLinksAddon)),
    loadOptionalAddon(WEBGL_JS, "xterm-webgl-addon", () => Boolean(globalThis.WebglAddon?.WebglAddon)),
  ]);

  const promoted = promoteTerminalConstructor();
  if (promoted) {
    const active = ["fit", "search"];
    if (linksReady) active.push("web-links");
    if (webglReady) active.push("webgl");
    document.documentElement.dataset.dcXtermAddons = active.join(",");
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
