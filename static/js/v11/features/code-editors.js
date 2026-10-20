const CODEMIRROR_JS = "/static/vendor/v11/codemirror.bundle.js";

let loadPromise = null;
let editor = null;
let source = null;
let host = null;
let lastTextareaValue = "";
let syncTimer = null;

function loadCodeMirror() {
  if (globalThis.DevConsoleCodeMirror?.createEditor) return Promise.resolve(globalThis.DevConsoleCodeMirror);
  if (loadPromise) return loadPromise;
  loadPromise = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = CODEMIRROR_JS;
    script.async = true;
    script.dataset.devconsoleV11 = "codemirror";
    script.addEventListener("load", () => resolve(globalThis.DevConsoleCodeMirror?.createEditor ? globalThis.DevConsoleCodeMirror : null), { once: true });
    script.addEventListener("error", () => resolve(null), { once: true });
    document.head.appendChild(script);
  });
  return loadPromise;
}

function modalVisible() {
  const modal = document.getElementById("envEditorModal");
  if (!modal) return false;
  const style = getComputedStyle(modal);
  return style.display !== "none" && style.visibility !== "hidden";
}

function syncFromTextarea(lib) {
  if (!editor || !source) return;
  const value = String(source.value || "");
  if (value !== lastTextareaValue) {
    lastTextareaValue = value;
    lib.setValue(editor, value);
  }
}

function startExternalSync(lib) {
  if (syncTimer) return;
  syncTimer = window.setInterval(() => {
    if (modalVisible()) syncFromTextarea(lib);
  }, 220);
}

async function installEnvEditor() {
  source = document.getElementById("envModalTextarea");
  if (!source || source.dataset.dcCodeMirror === "true") return Boolean(editor);

  const lib = await loadCodeMirror();
  if (!lib || !document.body.contains(source)) return false;

  host = document.createElement("div");
  host.className = "dc-v11-codemirror-host";
  source.insertAdjacentElement("beforebegin", host);
  lastTextareaValue = String(source.value || "");

  editor = lib.createEditor({
    parent: host,
    doc: lastTextareaValue,
    language: "env",
    onChange(value) {
      const next = String(value ?? "");
      lastTextareaValue = next;
      source.value = next;
      source.dispatchEvent(new Event("input", { bubbles: true }));
    },
  });

  source.dataset.dcCodeMirror = "true";
  source.classList.add("dc-v11-codemirror-source");
  document.documentElement.dataset.dcCodemirror = "6";
  startExternalSync(lib);

  const modal = document.getElementById("envEditorModal");
  if (modal) {
    const observer = new MutationObserver(() => {
      if (modalVisible()) {
        window.setTimeout(() => {
          syncFromTextarea(lib);
          lib.focus?.(editor);
        }, 30);
      }
    });
    observer.observe(modal, { attributes: true, attributeFilter: ["class", "style", "hidden"] });
  }
  return true;
}

export function bootCodeEditors() {
  installEnvEditor();
  if (!document.getElementById("envModalTextarea")) {
    const observer = new MutationObserver(() => {
      if (document.getElementById("envModalTextarea")) {
        observer.disconnect();
        installEnvEditor();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => observer.disconnect(), 10000);
  }
}
