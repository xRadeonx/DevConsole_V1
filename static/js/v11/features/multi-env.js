const ENV_ORDER = ["develop", "test", "main"];
const ENV_LABELS = {
  develop: "🟡 DEVELOP",
  test: "🔵 TEST",
  main: "🟢 MAIN",
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

function decorateMapSelector() {
  const select = document.getElementById("mapEnvSelect");
  if (!select) return;

  const previous = select.value || "develop";
  select.replaceChildren();
  for (const env of ENV_ORDER) {
    const option = document.createElement("option");
    option.value = env;
    option.textContent = `${ENV_LABELS[env]}${configured(env) ? "" : " · sin configurar"}`;
    option.disabled = !configured(env, "keycloak") || !configured(env, "database");
    select.appendChild(option);
  }

  if ([...select.options].some((option) => option.value === previous && !option.disabled)) {
    select.value = previous;
  } else {
    const first = [...select.options].find((option) => !option.disabled);
    select.value = first?.value || "develop";
  }

  select.title = "El entorno seleccionado se valida en backend; TEST/MAIN nunca reutilizan DEVELOP silenciosamente.";
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
      ? `${ENV_LABELS[env]}: Bitácora configurada`
      : `${ENV_LABELS[env]}: Bitácora no configurada. DevConsole mostrará el error real; no usará DEVELOP.`;
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

function installEnvironmentSummary() {
  const select = document.getElementById("mapEnvSelect");
  if (!select || document.getElementById("dcV11EnvSummary")) return;

  const summary = document.createElement("span");
  summary.id = "dcV11EnvSummary";
  summary.className = "dc-v11-env-summary";
  const available = ENV_ORDER.filter((env) => configured(env));
  summary.textContent = available.length
    ? `Disponibles: ${available.map((env) => env.toUpperCase()).join(" · ")}`
    : "Sin catálogo multi-entorno";
  summary.title = "Estado calculado sin exponer hosts, usuarios ni credenciales.";
  select.insertAdjacentElement("afterend", summary);
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
          if (payload?.success) {
            // dashboard.js keeps infrastructure targets in lexical memory. A
            // full same-origin reload is the safest way to rehydrate every V1
            // cache after changing the workspace root.
            window.setTimeout(() => window.location.reload(), 220);
          }
        }).catch(() => {});
      }
    } catch (_) {
      // Never interfere with the original request contract.
    }
    return response;
  };
}

export async function bootMultiEnvironment() {
  installRootChangeReload();
  await loadEnvironmentState();
  decorateMapSelector();
  decorateActivityButtons();
  repairInfrastructureMainButton();
  installEnvironmentSummary();

  window.addEventListener("focus", async () => {
    await loadEnvironmentState();
    decorateMapSelector();
    decorateActivityButtons();
  });

  return environmentState;
}
