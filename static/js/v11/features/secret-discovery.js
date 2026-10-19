const ENVIRONMENTS = ["develop", "test", "main"];
const ENV_LABEL = { develop: "DEVELOP", test: "TEST", main: "MAIN", global: "GLOBAL" };

const FRIENDLY = {
  "keycloak.develop.client_secret": "Keycloak · Client Secret",
  "keycloak.test.client_secret": "Keycloak · Client Secret",
  "keycloak.main.client_secret": "Keycloak · Client Secret",
  "databases.develop.bitacora_pass": "PostgreSQL Bitácora · Password",
  "databases.test.bitacora_pass": "PostgreSQL Bitácora · Password",
  "databases.main.bitacora_pass": "PostgreSQL Bitácora · Password",
  "databases.develop.contratos_pass": "PostgreSQL Contratos · Password",
  "databases.test.contratos_pass": "PostgreSQL Contratos · Password",
  "databases.main.contratos_pass": "PostgreSQL Contratos · Password",
  "databases.develop.destinaciones_pass": "PostgreSQL Destinaciones · Password",
  "databases.test.destinaciones_pass": "PostgreSQL Destinaciones · Password",
  "databases.main.destinaciones_pass": "PostgreSQL Destinaciones · Password",
  "infra.onlyoffice_jwt_secret": "OnlyOffice · JWT Secret",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function authHeaders() {
  const base = { "Content-Type": "application/json" };
  return typeof window.getAuthHeaders === "function" ? window.getAuthHeaders(base) : base;
}

function toast(message) {
  if (typeof window.showToast === "function") window.showToast(message);
}

function environmentForKey(key) {
  const match = String(key || "").match(/^(?:keycloak|databases)\.(develop|test|main)\./);
  return match?.[1] || "global";
}

function purposeForKey(key) {
  if (String(key).includes("bitacora_pass")) return "Actividad";
  if (String(key).includes("contratos_pass") || String(key).includes("destinaciones_pass")) {
    return "Mapa Operativo";
  }
  if (String(key).startsWith("keycloak.")) return "Mapa Operativo / sesiones";
  if (key === "infra.onlyoffice_jwt_secret") return "Infraestructura / OnlyOffice";
  return "DevConsole";
}

async function searchEnvironment(env) {
  const response = await fetch("/api/secrets/buscar", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ env }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.success === false) {
    throw new Error(payload?.message || payload?.error || `No se pudo revisar ${env.toUpperCase()}`);
  }
  return {
    env,
    findings: Array.isArray(payload?.hallazgos) ? payload.hallazgos : [],
    values: payload?.valores && typeof payload.valores === "object" ? payload.valores : {},
  };
}

function mergeResults(results) {
  const values = {};
  const findings = [];
  const seen = new Set();

  for (const result of results) {
    Object.assign(values, result.values || {});
    for (const item of result.findings || []) {
      const key = String(item?.clave || "");
      if (!key || seen.has(key)) continue;
      const itemEnv = environmentForKey(key);
      // The global OnlyOffice secret can be returned while scanning more than
      // one environment. Keep one row only.
      if (itemEnv !== "global" && itemEnv !== result.env) continue;
      seen.add(key);
      findings.push({ ...item, entorno: item.entorno || itemEnv });
    }
  }
  return { values, findings };
}

function renderFindings(body, findings) {
  if (!findings.length) {
    body.innerHTML = `
      <div class="dc-v11-secret-empty">
        No se encontraron credenciales concretas en los <code>.env</code> locales ni en los YAML de
        <code>config/</code>. DEVELOP usa el .env local; TEST y MAIN sólo aceptan fuentes propias de
        esos entornos para evitar reutilizar credenciales de DEVELOP por error.
      </div>`;
    return;
  }

  const grouped = new Map();
  for (const item of findings) {
    const env = item.entorno || environmentForKey(item.clave);
    if (!grouped.has(env)) grouped.set(env, []);
    grouped.get(env).push(item);
  }

  const order = ["develop", "test", "main", "global"];
  body.innerHTML = `
    <div class="dc-v11-secret-discovery">
      <div class="dc-v11-secret-group-title">CREDENCIALES DETECTADAS</div>
      <div class="dc-v11-secret-discovery-help">
        Selecciona sólo las que quieras copiar a <code>config/secrets.json</code>. Los valores no se
        muestran completos. Cada fila indica el entorno y el archivo de origen.
      </div>
      ${order.filter((env) => grouped.has(env)).map((env) => `
        <div class="dc-v11-secret-group" data-secret-env="${env}">
          <div class="dc-v11-secret-group-title">${ENV_LABEL[env] || env.toUpperCase()}</div>
          ${grouped.get(env).map((item) => {
            const key = String(item.clave || "");
            return `
              <label class="dc-v11-secret-discovery-row">
                <input type="checkbox" data-hallado="${escapeHtml(key)}" checked>
                <span>
                  <strong>${escapeHtml(FRIENDLY[key] || key)}</strong>
                  <small>${escapeHtml(purposeForKey(key))} · ${escapeHtml(item.fuente || "configuración local")}</small>
                  <small>Origen: ${escapeHtml(item.origen || "fuente local")} · valor ${escapeHtml(item.pista || "detectado")}</small>
                  <small class="dc-v11-secret-key">${escapeHtml(key)}</small>
                </span>
              </label>`;
          }).join("")}
        </div>`).join("")}
      <button class="btn dc-v11-secret-discovery-save" type="button" onclick="usarSecretosHallados()">
        💾 Guardar seleccionados
      </button>
    </div>`;
}

async function searchAllSecrets() {
  const body = document.getElementById("secretsBody");
  if (!body) return;
  body.innerHTML = `
    <div class="dc-v11-secret-loading">
      Buscando credenciales separadamente en DEVELOP, TEST y MAIN…
    </div>`;

  const settled = await Promise.allSettled(ENVIRONMENTS.map(searchEnvironment));
  const successes = settled.filter((item) => item.status === "fulfilled").map((item) => item.value);
  const failures = settled.filter((item) => item.status === "rejected");

  if (!successes.length) {
    const message = failures[0]?.reason?.message || "No fue posible realizar la búsqueda.";
    body.innerHTML = `<div class="dc-v11-secret-error">${escapeHtml(message)}</div>`;
    return;
  }

  const merged = mergeResults(successes);
  window.__secretosHallados = merged.values;
  renderFindings(body, merged.findings);

  const perEnv = ENVIRONMENTS.map((env) => {
    const count = merged.findings.filter((item) => environmentForKey(item.clave) === env).length;
    return `${env.toUpperCase()}: ${count}`;
  }).join(" · ");
  toast(`🔎 Credenciales detectadas — ${perEnv}`);

  if (failures.length) {
    const warning = document.createElement("div");
    warning.className = "dc-v11-secret-error";
    warning.textContent = `${failures.length} entorno(s) no pudieron revisarse; los demás resultados sí son válidos.`;
    body.prepend(warning);
  }
}

export function bootSecretDiscovery() {
  // Inline legacy buttons resolve this name through window at click time, so an
  // explicit override fixes the old hard-coded DEVELOP request without having
  // to fork the entire legacy dashboard script.
  window.buscarSecretosEnServicios = searchAllSecrets;
}
