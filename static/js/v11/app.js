import { events } from "./core/events.js";
import { features } from "./core/features.js";

function bootFoundation() {
  document.documentElement.dataset.devconsoleUi = "v1.1";
  document.documentElement.classList.add("dc-v11-foundation");

  const api = Object.freeze({
    version: "1.1",
    features,
    events,
  });

  Object.defineProperty(window, "DevConsoleV11", {
    value: api,
    configurable: false,
    enumerable: false,
    writable: false,
  });

  events.emit("v11-ready", {
    version: api.version,
    features: features.snapshot(),
  });
}

if (features.enabled("foundation")) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootFoundation, { once: true });
  } else {
    bootFoundation();
  }
}
