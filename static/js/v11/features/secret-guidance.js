const ENV_ORDER = ["develop", "test", "main"];
const ENV_LABEL = { develop: "DEVELOP", test: "TEST", main: "MAIN" };

let lastSecretPayload = null;
let lastEnvironmentState = null;
let discoveredValues = {};

function authHeaders() {
  if (typeof window.getAuthHeaders === "function") {
    return window.getAuthHeaders({ "Content-Type": "application/json" });
  }
  return { "Content-Type": "application/json" };
}

function toast(message) {
  if (typeof window.showToast === "function") window.showToast(message);
  else console.info(message);
}

function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function secretMeta(key) {
  if (key === "infra.onlyoffice_jwt_secret") {
    return {
      group: "infra",
      env: "local",
      title: "OnlyOffice · JWT Secret",
      help: "Infraestructura local · autentica DocumentServer/OnlyOffice.",
      placeholder: "Ingresar JWT_SECRET de OnlyOffice",
    };
  }

  let match = key.match(/^keycloak\.(develop|test|main)\.client_secret$/);
  if (match) {
    const env = match[1];
    return {
      group: env,
      env,
      title: "Keycloak · Client Secret",
      help: `${ENV_LABEL[env]} · requerido por Mapa Operativo y consultas de sesión.`,
      placeholder: `Ingresar client secret de Keycloak ${ENV_LABEL[env]}`,
    };
  }

  match = key.match(/^databases\.(develop|test|main)\.(bitacora|contratos|destinaciones)_pass$/);
  if (match) {
    const [, env, logical] = match;
    const labels = {
      bitacora: ["PostgreSQL Bitácora · Password", "Actividad"],
      contratos: ["PostgreSQL Contratos · Password", "Mapa Operativo"],
      destinaciones: ["PostgreSQL Destinaciones · Password", "Mapa Operativo"],
    };
    return {
      group: env,
      env,
      title: labels[logical][0],
      help: `${ENV_LABEL[env]} · requerido por ${labels[logical][1]}.`,
      placeholder: `Ingresar contraseña de ${logical} ${ENV_LABEL[env]}`,
    };
  }

  return {
    group: "other",
    env: "",
    title: key,
    help: "Credencial requerida por la configuración local.",
    placeholder: "Ingresar valor",
  };
}

function missingLabel(item) {
  const labels = {
    keycloak_endpoint: "endpoint/realm/client_id de Keycloak",
    keycloak_credentials: "client secret de Keycloak",
    database_endpoint: "host/puerto de PostgreSQL",
    map_database_credentials: "credenciales de Contratos/Destinaciones",
    activity_database_credentials: "credencial de Bitácora",
  };
  return labels[item] || item;
}

function createCapabilityCard(env, state = {}) {
  const card = element("div", "dc-v11-secret-capability");
  const title = element("div", "dc-v11-secret-capability-title", ENV_LABEL[env]);
  const chips = element("div", "dc-v11-secret-capability-chips");

  const map = element("span", `dc-v11-secret-chip ${state.map ? "is-ready" : "is-missing"}`);
  map.textContent = state.map ? "✓ Mapa listo" : "⚠ Mapa pendiente";
  const activity = element("span", `dc-v11-secret-chip ${state.activity ? "is-ready" : "is-missing"}`);
  activity.textContent = state.activity ? "✓ Actividad lista" : "⚠ Actividad pendiente";
  chips.append(map, activity);
  card.append(title, chips);

  if (Array.isArray(state.missing) && state.missing.length) {
    const detail = element("div", "dc-v11-secret-capability-detail");
    detail.textContent = `Falta: ${state.missing.map(missingLabel).join(" · ")}`;
    card.appendChild(detail);
  }
  return card;
}

function createField(item) {
  const key = String(item.ruta || "");
  const configured = Boolean(item.configurada);
  const meta = secretMeta(key);
  const field = element("label", "dc-v11-secret-field");

  const header = element("div", "dc-v11-secret-field-head");
  const text = element("div", "dc-v11-secret-field-copy");
  text.append(
    element("strong", "dc-v11-secret-field-title", meta.title),
    element("span", "dc-v11-secret-field-help", meta.help),
  );
  const status = element(
    "span",
    `dc-v11-secret-state ${configured ? "is-saved" : "is-missing"}`,
    configured ? `✓ Guardado${meta.env && meta.env !== "local" ? ` para ${ENV_LABEL[meta.env]}` : ""}` : "⚠ Falta",
  );
  header.append(text, status);

  const input = document.createElement("input");
  input.type = "password";
  input.className = "search-input dc-v11-secret-input";
  input.dataset.secretKey = key;
  input.autocomplete = "new-password";
  input.placeholder = configured
    ? `${meta.title} guardado — deja vacío para conservarlo`
    : meta.placeholder;

  const technical = element("code", "dc-v11-secret-key", key);
  field.append(header, input, technical);
  return field;
}

function createGroup(title, items) {
  const section = element("section", "dc-v11-secret-group");
  const heading = element("div", "dc-v11-secret-group-title", title);
  section.appendChild(heading);
  for (const item of items) section.appendChild(createField(item));
  return section;
}

function createDiscoveryPanel(hallazgos = []) {
  document.getElementById("dcV11SecretDiscovery")?.remove();
  if (!hallazgos.length) return null;

  const panel = element("div", "dc-v11-secret-discovery");
  panel.id = "dcV11SecretDiscovery";
  panel.appendChild(element("strong", "", `Encontradas ${hallazgos.length} credencial(es) reutilizables`));
  panel.appendChild(
    element(
      "div",
      "dc-v11-secret-discovery-help",
      "Se detectaron en .env o en YAML del directorio config/. Revisa el origen y guarda sólo las que correspondan.",
    ),
  );

  for (const hit of hallazgos) {
    const row = element("label", "dc-v11-secret-discovery-row");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = true;
    check.dataset.discoveredKey = String(hit.clave || "");
    const copy = element("span", "");
    const meta = secretMeta(String(hit.clave || ""));
    const strong = element("strong", "", meta.title);
    const detail = element("small", "", `${meta.env && meta.env !== "local" ? `${ENV_LABEL[meta.env]} · ` : ""}${hit.origen || "origen local"} · ${hit.pista || "••••"}`);
    copy.append(strong, detail);
    row.append(check, copy);
    panel.appendChild(row);
  }

  const save = element("button", "btn dc-v11-secret-discovery-save", "💾 Usar seleccionadas");
  save.type = "button";
  save.addEventListener("click", saveDiscoveredSecrets);
  panel.appendChild(save);
  return panel;
}

function renderEditor(payload, envState) {
  const body = document.getElementById("secretsBody");
  if (!body) return;
  body.replaceChildren();
  body.classList.add("dc-v11-secret-body");

  const intro = element("div", "dc-v11-secret-intro");
  intro.appendChild(
    element(
      "div",
      "",
      "DevConsole separa cada credencial por entorno y por función. Los valores guardados nunca se muestran; el estado sólo confirma a qué módulo pertenecen.",
    ),
  );
  const note = element(
    "div",
    "dc-v11-secret-config-note",
    "Endpoints, hosts, nombres de BD y usuarios NO son secretos. V1.1 intenta recuperarlos automáticamente desde la carpeta config/ y sus YAML; si no existen allí, se declaran en panel.json.",
  );
  intro.appendChild(note);

  const actions = element("div", "dc-v11-secret-toolbar");
  const discover = element("button", "btn btn-outline", "🔎 Buscar en .env + config YAML");
  discover.type = "button";
  discover.addEventListener("click", discoverSecrets);
  const refresh = element("button", "btn btn-outline", "↻ Actualizar estado");
  refresh.type = "button";
  refresh.addEventListener("click", loadAndRender);
  actions.append(discover, refresh);
  intro.appendChild(actions);
  body.appendChild(intro);

  const capabilities = element("div", "dc-v11-secret-capabilities");
  for (const env of ENV_ORDER) {
    capabilities.appendChild(createCapabilityCard(env, envState?.environments?.[env] || {}));
  }
  body.appendChild(capabilities);

  const keys = Array.isArray(payload?.claves) ? payload.claves : [];
  const byGroup = { develop: [], test: [], main: [], infra: [], other: [] };
  for (const item of keys) {
    const group = secretMeta(String(item.ruta || "")).group;
    (byGroup[group] || byGroup.other).push(item);
  }

  for (const env of ENV_ORDER) {
    if (byGroup[env].length) body.appendChild(createGroup(ENV_LABEL[env], byGroup[env]));
  }
  if (byGroup.infra.length) body.appendChild(createGroup("INFRAESTRUCTURA LOCAL", byGroup.infra));
  if (byGroup.other.length) body.appendChild(createGroup("OTRAS CREDENCIALES", byGroup.other));

  if (!keys.length) {
    body.appendChild(element("div", "dc-v11-secret-empty", "No hay credenciales declaradas para esta instalación."));
  }
}

async function loadAndRender() {
  const body = document.getElementById("secretsBody");
  if (body) {
    body.replaceChildren(element("div", "dc-v11-secret-loading", "Consultando requisitos y catálogo local…"));
  }
  try {
    const [secretRes, envRes] = await Promise.all([
      fetch("/api/secrets", { cache: "no-store" }),
      fetch("/api/v1.1/environments", { cache: "no-store" }),
    ]);
    if (!secretRes.ok) throw new Error(`Secretos: HTTP ${secretRes.status}`);
    lastSecretPayload = await secretRes.json();
    lastEnvironmentState = envRes.ok ? await envRes.json() : null;
    const path = document.getElementById("secretsPath");
    if (path && lastSecretPayload?.archivo) path.textContent = lastSecretPayload.archivo;
    renderEditor(lastSecretPayload, lastEnvironmentState);
  } catch (error) {
    if (body) body.replaceChildren(element("div", "dc-v11-secret-error", String(error?.message || error)));
  }
}

async function discoverSecrets() {
  const body = document.getElementById("secretsBody");
  const button = body?.querySelector(".dc-v11-secret-toolbar button");
  if (button) {
    button.disabled = true;
    button.textContent = "Buscando en DEVELOP / TEST / MAIN…";
  }

  const hits = [];
  discoveredValues = {};
  try {
    for (const env of ENV_ORDER) {
      const response = await fetch("/api/secrets/buscar", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ env }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.message || payload?.error || `HTTP ${response.status}`);
      }
      for (const hit of payload.hallazgos || []) {
        if (!hits.some((current) => current.clave === hit.clave)) hits.push(hit);
      }
      Object.assign(discoveredValues, payload.valores || {});
    }

    const panel = createDiscoveryPanel(hits);
    if (panel && body) body.insertBefore(panel, body.querySelector(".dc-v11-secret-capabilities") || body.firstChild?.nextSibling || null);
    if (!hits.length) toast("ℹ️ No se encontraron credenciales reutilizables en .env ni config YAML.");
  } catch (error) {
    toast(`⚠️ ${String(error?.message || error)}`);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "🔎 Buscar en .env + config YAML";
    }
  }
}

async function saveDiscoveredSecrets() {
  const selected = {};
  document.querySelectorAll("#dcV11SecretDiscovery [data-discovered-key]").forEach((checkbox) => {
    if (!checkbox.checked) return;
    const key = checkbox.dataset.discoveredKey;
    if (key && discoveredValues[key]) selected[key] = discoveredValues[key];
  });
  if (!Object.keys(selected).length) {
    toast("⚠️ No seleccionaste ninguna credencial.");
    return;
  }

  try {
    const response = await fetch("/api/secrets/guardar", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ valores: selected }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.success === false) {
      throw new Error(payload?.message || `HTTP ${response.status}`);
    }
    toast(`✓ ${Object.keys(selected).length} credencial(es) guardadas.`);
    document.dispatchEvent(new CustomEvent("devconsole:v11-environments-updated"));
    await loadAndRender();
  } catch (error) {
    toast(`⚠️ ${String(error?.message || error)}`);
  }
}

function openGuidedSecretsModal() {
  if (typeof window.ensureDevOrAdminAuth === "function" && !window.ensureDevOrAdminAuth()) return;
  const modal = document.getElementById("secretsModal");
  if (modal) modal.style.display = "flex";
  loadAndRender();
}

export function bootSecretGuidance() {
  // dashboard.js is a classic script loaded before this module, so its public
  // modal function is available here. Replace only the renderer; existing save
  // and close actions keep their V1 contracts.
  window.openSecretsModal = openGuidedSecretsModal;
  window.buscarSecretosEnServicios = discoverSecrets;
  document.documentElement.dataset.dcSecretGuidance = "v1.1";
}
