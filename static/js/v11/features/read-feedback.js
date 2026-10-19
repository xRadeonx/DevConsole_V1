const ROUTES = [
  { match: "/api/analytics/connections", tab: "#tab-map", id: "map" },
  { match: "/api/activity/feed", tab: "#tab-activity", id: "activity" },
  { match: "/api/activity/detail", tab: "#tab-activity", id: "activity" },
  { match: "/api/infra/targets", tab: "#tab-infra", id: "infra" },
];

let installed = false;

function noticeTarget(selector) {
  return document.querySelector(selector);
}

function clearNotice(id) {
  document.getElementById(`dcV11ReadNotice-${id}`)?.remove();
}

function showNotice(route, title, message) {
  const tab = noticeTarget(route.tab);
  if (!tab) return;
  let notice = document.getElementById(`dcV11ReadNotice-${route.id}`);
  if (!notice) {
    notice = document.createElement("div");
    notice.id = `dcV11ReadNotice-${route.id}`;
    notice.className = "dc-v11-read-notice";
    tab.prepend(notice);
  }
  notice.innerHTML = `<span aria-hidden="true">⚠</span><div><strong>${title}</strong><br>${message}</div>`;
}

function routeFor(url) {
  return ROUTES.find((route) => String(url || "").includes(route.match));
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
          `Detectados: ${available.length ? available.map((item) => item.toUpperCase()).join(" · ") : "ninguno"}. TEST/MAIN requieren configuración local; DevConsole ya no usa DEVELOP como sustituto.`,
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
        `Configuración local incompleta para ${env}`,
        "El entorno no será sustituido por DEVELOP. Revisa el catálogo local y el botón 🔐 Secretos; las credenciales se guardan sólo en config/secrets.json.",
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
