const loadedScripts = new Map();

function loadScript(src) {
  if (loadedScripts.has(src)) return loadedScripts.get(src);
  const promise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[data-v11-src="${src}"]`);
    if (existing) { resolve(); return; }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.dataset.v11Src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
    document.head.appendChild(script);
  });
  loadedScripts.set(src, promise);
  return promise;
}

export async function loadTerminalAddons() {
  const results = { fit: false, search: false, clipboard: !!navigator.clipboard, weblinks: true };
  try {
    await loadScript('/static/vendor/terminal-lab/addon-fit.js');
    results.fit = !!(window.FitAddon && window.FitAddon.FitAddon);
  } catch (_) {}
  try {
    await loadScript('/static/vendor/terminal-lab/addon-search.js');
    results.search = !!(window.SearchAddon && window.SearchAddon.SearchAddon);
  } catch (_) {}
  return results;
}

export async function enhanceTerminal(term, hostElement) {
  const state = { fit: null, search: null, resizeObserver: null };
  const available = await loadTerminalAddons();
  if (available.fit && term && typeof term.loadAddon === 'function') {
    state.fit = new window.FitAddon.FitAddon();
    term.loadAddon(state.fit);
    try { state.fit.fit(); } catch (_) {}
    if (hostElement && window.ResizeObserver) {
      state.resizeObserver = new ResizeObserver(() => {
        try { state.fit.fit(); } catch (_) {}
      });
      state.resizeObserver.observe(hostElement);
    }
  }
  if (available.search && term && typeof term.loadAddon === 'function') {
    state.search = new window.SearchAddon.SearchAddon();
    term.loadAddon(state.search);
  }
  return {
    available,
    findNext: (value, options) => state.search ? state.search.findNext(value, options) : false,
    findPrevious: (value, options) => state.search ? state.search.findPrevious(value, options) : false,
    fit: () => { if (state.fit) state.fit.fit(); },
    copySelection: async () => {
      if (!navigator.clipboard || !term || typeof term.getSelection !== 'function') return false;
      const text = term.getSelection();
      if (!text) return false;
      await navigator.clipboard.writeText(text);
      return true;
    },
    dispose: () => state.resizeObserver && state.resizeObserver.disconnect(),
  };
}
