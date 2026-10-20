const ROUTES = [
  { match: "/api/analytics/connections", tab: "#tab-map", id: "map" },
  { match: "/api/activity/feed", tab: "#tab-activity", id: "activity" },
  { match: "/api/activity/detail", tab: "#tab-activity", id: "activity" },
  { match: "/api/infra/targets", tab: "#tab-infra", id: "infra" },
];

const MISSING_LABELS = {
  keycloak_endpoint: "endpoint/realm/client_id de Keycloak (catálogo, no secreto)",
  keycloak_credentials: "client secret de Keycloak",
  database_endpoint: "host/puerto de PostgreSQL (catálogo, no secreto)",
  map_database_credentials: "usuarios/contraseñas de Contratos y Destinaciones",
  activity_database_credentials: "usuario/contraseña de Bitácora",
};

let installed = false;

function noticeTarget(selector) {
  return document.querySelector(selector);
}

function clearNotice(id) {
  document.getElementById(`dcV11ReadNotice-${id}`)?.remove();
}

function showNotice(route, title, message, action = null) {
  const tab = noticeTarget(route.tab);
  if (!tab) return;
  let notice = document.getElementById(`dcV11ReadNotice-${route.id}`);
  if (!notice) {
    notice = document.createElement("div");
    notice.id = `dcV11ReadNotice-${route.id}`;
    notice.className = "dc-v11-read-notice";
    tab.prepend(notice);
  }

  notice.replaceChildren();
  const icon = document.createElement("span");
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "⚠";

  const body = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = String(title || "Aviso");
  const text = document.createElement("div");
  text.textContent = String(message || "");
  body.append(strong, text);

  if (action?.label && typeof action.run === "function") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "dc-v11-notice-action";
    button.textContent = action.label;
    button.addEventListener("click", action.run);
    body.appendChild(button);
  }

  notice.append(icon, body);
}

function openSecrets() {
  if (typeof window.openSecretsModal === "function") window.openSecretsModal();
}

function openRole() {
  if (typeof window.openRoleModal === "function") window.openRoleModal();
  else document.getElementById("sidebarRolePill")?.click();
}

function routeFor(url) {
  return ROUTES.find((route) => String(url || "").includes(route.match));
}

function missingText(payload) {
  const missing = Array.isArray(payload?.missing) ? payload.missing : [];
  if (!missing.length) return "Falta completar el catálogo o las credenciales del entorno.";
  return `Pendiente: ${missing.map((item) => MISSING_LABELS[item] || item).join(" · ")}.`;
}

function inspectJson(route, response) {
  response.clone().json().then((payload) => {
    if (route.id === "infra") {
      const environments = payload?.environments;
      const available = environments && typeof environments === "object"
        ? Object.keys(environments).filter((key) => Array.isArray(environments[key]) && environments[key].length)
        : [];
      if (available.length < 3) {
        showNotice(
          route,
          "Catálogo de infraestructura incompleto",
          `Detectados: ${available.length ? available.map((item) => item.toUpperCase()).join(" · ") : "ninguno"}. V1.1 intenta recuperar endpoints desde config/*.yaml y nunca sustituye TEST/MAIN por DEVELOP.`,
          { label: "🔐 Ver requisitos", run: openSecrets },
        );
      } else {
        clearNotice(route.id);
      }
      return;
    }

    if (payload?.configuration_missing) {
      const env = String(payload.requested_env || payload.env || "entorno").toUpperCase();
      showNotice(
        route,
        `Configuración incompleta para ${env}`,
        `${missingText(payload)} Los endpoints/usuarios se intentan detectar desde config YAML; las contraseñas y client secrets se administran en Secretos.`,
        { label: "🔐 Ver requisitos y autodetectar", run: openSecrets },
      );
    } else if (payload?.success !== false) {
      clearNotice(route.id);
    }
  }).catch(() => {});
}

export function bootReadFeedback() {
  if (installed) return;
  installed = true;
  const nativeFetch = window.fetch.bind(window);

  window.fetch = async function devConsoleReadFeedbackFetch(input, init = {}) {
    const response = await nativeFetch(input, init);
    try {
      const url = typeof input === "string" ? input : input?.url || "";
      const route = routeFor(url);
      if (!route) return response;

      if (response.status === 403) {
        showNotice(
          route,
          "Vista protegida",
          "Esta telemetría contiene información operacional sensible y requiere una sesión Administrador válida. La vista ya no queda vacía silenciosamente.",
          { label: "🔑 Autenticar Administrador", run: openRole },
        );
      } else if (response.ok) {
        inspectJson(route, response);
      }
    } catch (_) {
      // Feedback is additive; never alter the original fetch result.
    }
    return response;
  };
}
