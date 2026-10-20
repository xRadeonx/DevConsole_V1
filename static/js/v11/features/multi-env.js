const ENV_ORDER = ["develop", "test", "main"];
const ENV_LABELS = {
  develop: "🟡 DEVELOP",
  test: "🔵 TEST",
  main: "🟢 MAIN",
};
const CATALOG_LABELS = {
  "legacy-local": "Catálogo V1 local",
  "v1.1-local-config": "Configuración V1.1 local",
  "workspace-discovery": "Sólo .env del workspace",
  none: "Sin catálogo",
};

let environmentState = null;
let fetchWrapped = false;

async function loadEnvironmentState() {
  try {
    const response = await fetch("/api/v1.1/environments", { cache: "no-store" });
    if (!response.ok) return null;
    environmentState = await response.json();
    return environmentState;
  } catch (error) {
    console.debug("[v1.1/multi-env] environment status unavailable", error);
    return null;
  }
}

function configured(env, capability = "configured") {
  const state = environmentState?.environments?.[env];
  return Boolean(state && state[capability]);
}

function missingLabels(env) {
  const missing = environmentState?.environments?.[env]?.missing;
  if (!Array.isArray(missing)) return [];
  const labels = {
    keycloak_endpoint: "endpoint Keycloak",
    keycloak_credentials: "credencial Keycloak",
    database_endpoint: "endpoint BD",
    map_database_credentials: "credenciales Contratos/Destinaciones",
    activity_database_credentials: "credencial Bitácora",
  };
  return missing.map((item) => labels[item] || item);
}

function decorateMapSelector() {
  const select = document.getElementById("mapEnvSelect");
  if (!select) return;

  const previous = select.value || "develop";
  select.replaceChildren();
  for (const env of ENV_ORDER) {
    const option = document.createElement("option");
    const inCatalog = configured(env);
    const ready = configured(env, "map");
    option.value = env;
    option.textContent = `${ENV_LABELS[env]}${!inCatalog ? " · sin catálogo" : !ready ? " · credenciales pendientes" : ""}`;
    option.disabled = !ready;
    option.title = ready
      ? `${ENV_LABELS[env]} listo para Mapa Operativo`
      : `Pendiente: ${missingLabels(env).join(", ") || "configuración local"}`;
    select.appendChild(option);
  }

  if ([...select.options].some((option) => option.value === previous && !option.disabled)) {
    select.value = previous;
  } else {
    const first = [...select.options].find((option) => !option.disabled);
    select.value = first?.value || "develop";
  }

  select.title = "El entorno se valida en backend; TEST/MAIN nunca reutilizan DEVELOP silenciosamente.";
}

function decorateActivityButtons() {
  const mapping = {
    develop: "btnActEnvDev",
    test: "btnActEnvTest",
    main: "btnActEnvMain",
  };
  for (const [env, id] of Object.entries(mapping)) {
    const button = document.getElementById(id);
    if (!button) continue;
    const available = configured(env, "activity");
    button.classList.toggle("dc-v11-env-unavailable", !available);
    button.setAttribute("aria-disabled", available ? "false" : "true");
    button.title = available
      ? `${ENV_LABELS[env]}: Bitácora lista`
      : `${ENV_LABELS[env]}: ${missingLabels(env).join(", ") || "Bitácora no configurada"}`;
  }
}

function decorateInfrastructureButtons() {
  const mapping = {
    develop: "infraTab_develop",
    test: "infraTab_test",
    main: document.getElementById("infraTab_main") ? "infraTab_main" : "infraTab_prod",
  };
  for (const [env, id] of Object.entries(mapping)) {
    const button = document.getElementById(id);
    if (!button) continue;
    const available = configured(env);
    button.classList.toggle("dc-v11-env-unavailable", !available);
    button.title = available
      ? `${ENV_LABELS[env]} detectado en el catálogo local`
      : `${ENV_LABELS[env]} no figura en el catálogo detectado`;
  }
}

function repairInfrastructureMainButton() {
  const button = document.getElementById("infraTab_prod");
  if (!button) return;
  button.textContent = "🟢 MAIN";
  button.setAttribute("onclick", "setInfraView('main')");
  button.addEventListener("click", () => {
    requestAnimationFrame(() => {
      button.classList.add("active");
      button.style.background = "#2563eb";
      button.style.color = "#fff";
    });
  });
}

function renderEnvironmentSummary() {
  const select = document.getElementById("mapEnvSelect");
  if (!select) return;

  let summary = document.getElementById("dcV11EnvSummary");
  if (!summary) {
    summary = document.createElement("span");
    summary.id = "dcV11EnvSummary";
    summary.className = "dc-v11-env-summary";
    select.insertAdjacentElement("afterend", summary);
  }

  const available = ENV_ORDER.filter((env) => configured(env));
  const mapReady = ENV_ORDER.filter((env) => configured(env, "map"));
  const activityReady = ENV_ORDER.filter((env) => configured(env, "activity"));
  const source = environmentState?.catalog?.source || "none";
  const sourceName = environmentState?.catalog?.source_name || "";
  const sourceLabel = CATALOG_LABELS[source] || source;
  const envText = available.length
    ? available.map((env) => env.toUpperCase()).join(" · ")
    : "ninguno";
  summary.textContent = `${sourceLabel}: ${envText}`;
  summary.title = [
    sourceName ? `Fuente: ${sourceName}` : "Sin fuente multi-entorno detectada",
    `Mapa listo: ${mapReady.length ? mapReady.map((env) => env.toUpperCase()).join(" · ") : "ninguno"}`,
    `Actividad lista: ${activityReady.length ? activityReady.map((env) => env.toUpperCase()).join(" · ") : "ninguno"}`,
    "No se exponen hosts, usuarios ni credenciales.",
  ].join(" | ");
  summary.dataset.catalogSource = source;
}

function installRootChangeReload() {
  if (fetchWrapped) return;
  fetchWrapped = true;
  const nativeFetch = window.fetch.bind(window);

  window.fetch = async function devConsoleV11Fetch(input, init = {}) {
    const response = await nativeFetch(input, init);
    try {
      const url = typeof input === "string" ? input : input?.url || "";
      const method = String(init?.method || (typeof input !== "string" ? input?.method : "GET") || "GET").toUpperCase();
      if (method === "POST" && url.includes("/api/root_dir/set") && response.ok) {
        const clone = response.clone();
        clone.json().then((payload) => {
          if (payload?.success) window.setTimeout(() => window.location.reload(), 220);
        }).catch(() => {});
      } else if (method === "POST" && url.includes("/api/secrets/guardar") && response.ok) {
        window.setTimeout(async () => {
          await loadEnvironmentState();
          refreshDecorations();
        }, 160);
      }
    } catch (_) {
      // Never interfere with the original request contract.
    }
    return response;
  };
}

function refreshDecorations() {
  decorateMapSelector();
  decorateActivityButtons();
  decorateInfrastructureButtons();
  renderEnvironmentSummary();
}

export async function bootMultiEnvironment() {
  installRootChangeReload();
  await loadEnvironmentState();
  repairInfrastructureMainButton();
  refreshDecorations();

  window.addEventListener("focus", async () => {
    await loadEnvironmentState();
    refreshDecorations();
  });

  return environmentState;
}
