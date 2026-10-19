import { events } from "./core/events.js";
import { features } from "./core/features.js";
import { bootMultiEnvironment } from "./features/multi-env.js";
import { bootTerminalAddons } from "./features/terminal-addons.js";

async function bootFoundation() {
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

  const environmentState = await bootMultiEnvironment();
  // xterm core + Fit/Search are self-hosted. Loading is deferred to an idle
  // slot so the dashboard remains fast while the real terminal gains resize
  // and search capabilities automatically.
  bootTerminalAddons();

  events.emit("v11-ready", {
    version: api.version,
    features: features.snapshot(),
    environments: environmentState?.available || [],
  });
}

if (features.enabled("foundation")) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootFoundation, { once: true });
  } else {
    bootFoundation();
  }
}
