const STORAGE_KEY = "devconsole.v11.features";

const DEFAULTS = Object.freeze({
  foundation: true,
  splitPanels: false,
  enhancedTables: false,
  codeEditor: false,
  terminalAddons: false,
});

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const value = raw ? JSON.parse(raw) : {};
    return value && typeof value === "object" ? value : {};
  } catch (_error) {
    return {};
  }
}

let state = { ...DEFAULTS, ...readStored() };

export function enabled(name) {
  return Boolean(state[name]);
}

export function snapshot() {
  return Object.freeze({ ...state });
}

export function setFeature(name, value) {
  if (!(name in DEFAULTS)) {
    throw new Error(`Unknown V1.1 feature: ${name}`);
  }
  state = { ...state, [name]: Boolean(value) };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (_error) {
    // Storage may be disabled by browser policy; the in-memory flag still works.
  }
  document.dispatchEvent(
    new CustomEvent("devconsole:v11-feature-change", {
      detail: { name, value: Boolean(value), features: snapshot() },
    }),
  );
  return Boolean(value);
}

export const features = Object.freeze({ enabled, snapshot, setFeature });
