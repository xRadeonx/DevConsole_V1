const CODEMIRROR_JS = "/static/vendor/v11/codemirror.bundle.js";

let loadPromise = null;
let editor = null;
let source = null;
let host = null;
let toolbar = null;
let baselineValue = "";
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

function currentValue(lib) {
  if (editor && lib?.getValue) return String(lib.getValue(editor) || "");
  return String(source?.value || "");
}

function analyseEnv(value) {
  const lines = String(value || "").split(/\r?\n/);
  const seen = new Map();
  const issues = [];
  const sensitive = [];
  let assignments = 0;

  lines.forEach((raw, index) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    const equals = line.indexOf("=");
    if (equals <= 0) {
      issues.push(`L${index + 1}: falta KEY=valor`);
      return;
    }
    const key = line.slice(0, equals).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
      issues.push(`L${index + 1}: clave inválida (${key || "vacía"})`);
      return;
    }
    assignments += 1;
    if (seen.has(key)) {
      issues.push(`L${index + 1}: ${key} duplicada (primera en L${seen.get(key)})`);
    } else {
      seen.set(key, index + 1);
    }
    if (/(PASS|PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|JWT)/i.test(key)) {
      sensitive.push(key);
    }
  });

  return {
    lines: lines.length,
    assignments,
    issues,
    sensitive: [...new Set(sensitive)],
  };
}

function setBadge(role, text, state = "neutral", title = "") {
  const badge = toolbar?.querySelector(`[data-role="${role}"]`);
  if (!badge) return;
  badge.textContent = text;
  badge.dataset.state = state;
  badge.title = title;
}

function refreshToolbar(lib) {
  if (!toolbar) return;
  const value = currentValue(lib);
  const report = analyseEnv(value);
  const modified = value !== baselineValue;

  setBadge(
    "validity",
    report.issues.length ? `${report.issues.length} problema${report.issues.length === 1 ? "" : "s"}` : "ENV válido",
    report.issues.length ? "warning" : "success",
    report.issues.length ? report.issues.slice(0, 8).join("\n") : "Sintaxis KEY=valor y claves sin duplicar",
  );
  setBadge(
    "dirty",
    modified ? "Modificado" : "Sin cambios",
    modified ? "warning" : "neutral",
    modified ? "Hay cambios pendientes respecto del contenido cargado" : "Sin cambios respecto del contenido cargado",
  );
  setBadge(
    "stats",
    `${report.assignments} vars · ${report.lines} líneas`,
    "neutral",
    `${report.assignments} asignaciones detectadas`,
  );
  setBadge(
    "sensitive",
    report.sensitive.length ? `${report.sensitive.length} sensible${report.sensitive.length === 1 ? "" : "s"}` : "Sin sensibles",
    report.sensitive.length ? "danger" : "neutral",
    report.sensitive.length
      ? `Claves potencialmente sensibles (no se muestran valores): ${report.sensitive.join(", ")}`
      : "No se detectaron nombres de variables típicamente sensibles",
  );
}

function createToolbar(lib) {
  const bar = document.createElement("div");
  bar.className = "dc-v11-editor-toolbar";
  bar.innerHTML = `
    <div class="dc-v11-editor-heading">
      <span class="dc-v11-editor-product">CodeMirror 6</span>
      <span class="dc-v11-editor-subtitle">Editor .env con validación local</span>
    </div>
    <div class="dc-v11-editor-badges" aria-live="polite">
      <span class="dc-v11-editor-badge" data-role="validity" data-state="neutral">Validando…</span>
      <span class="dc-v11-editor-badge" data-role="dirty" data-state="neutral">Sin cambios</span>
      <span class="dc-v11-editor-badge" data-role="stats" data-state="neutral">0 vars</span>
      <span class="dc-v11-editor-badge" data-role="sensitive" data-state="neutral">Sin sensibles</span>
    </div>
    <div class="dc-v11-editor-actions">
      <button type="button" data-action="find" title="Enfoca el editor. Usa Ctrl+F para la búsqueda nativa de CodeMirror.">⌕ Buscar</button>
      <button type="button" data-action="validate" title="Valida sintaxis KEY=valor y variables duplicadas sin enviar contenido al servidor.">✓ Validar</button>
      <button type="button" data-action="copy" title="Copia el contenido actual del editor.">⧉ Copiar</button>
    </div>
  `;

  bar.querySelector('[data-action="find"]').addEventListener("click", () => {
    lib.focus?.(editor);
    const hint = bar.querySelector('[data-role="validity"]');
    if (hint) hint.title = `${hint.title || ""}\nBúsqueda: Ctrl+F / Cmd+F dentro del editor.`.trim();
  });
  bar.querySelector('[data-action="validate"]').addEventListener("click", () => {
    refreshToolbar(lib);
    const badge = bar.querySelector('[data-role="validity"]');
    badge?.classList.add("is-pulsing");
    window.setTimeout(() => badge?.classList.remove("is-pulsing"), 520);
  });
  bar.querySelector('[data-action="copy"]').addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(currentValue(lib));
      const button = bar.querySelector('[data-action="copy"]');
      const previous = button.textContent;
      button.textContent = "✓ Copiado";
      window.setTimeout(() => { button.textContent = previous; }, 900);
    } catch (_) {
      // Clipboard permissions vary by browser; the editor remains fully usable.
    }
  });
  return bar;
}

function syncFromTextarea(lib) {
  if (!editor || !source) return;
  const value = String(source.value || "");
  if (value !== lastTextareaValue) {
    lastTextareaValue = value;
    baselineValue = value;
    lib.setValue(editor, value);
    refreshToolbar(lib);
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

  toolbar = createToolbar(lib);
  source.insertAdjacentElement("beforebegin", toolbar);

  host = document.createElement("div");
  host.className = "dc-v11-codemirror-host";
  source.insertAdjacentElement("beforebegin", host);
  lastTextareaValue = String(source.value || "");
  baselineValue = lastTextareaValue;

  editor = lib.createEditor({
    parent: host,
    doc: lastTextareaValue,
    language: "env",
    onChange(value) {
      const next = String(value ?? "");
      lastTextareaValue = next;
      source.value = next;
      source.dispatchEvent(new Event("input", { bubbles: true }));
      refreshToolbar(lib);
    },
  });

  source.dataset.dcCodeMirror = "true";
  source.classList.add("dc-v11-codemirror-source");
  document.documentElement.dataset.dcCodemirror = "6";
  refreshToolbar(lib);
  startExternalSync(lib);

  const modal = document.getElementById("envEditorModal");
  if (modal) {
    const observer = new MutationObserver(() => {
      if (modalVisible()) {
        window.setTimeout(() => {
          syncFromTextarea(lib);
          baselineValue = currentValue(lib);
          refreshToolbar(lib);
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
