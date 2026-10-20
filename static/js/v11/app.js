import { events } from "./core/events.js";
import { features } from "./core/features.js";
import { bootMultiEnvironment } from "./features/multi-env.js";
import { bootReadFeedback } from "./features/read-feedback.js";
import { bootTerminalAddons } from "./features/terminal-addons.js";
import { bootSplitLayouts } from "./features/split-layouts.js";
import { bootGridEnhancements } from "./features/grid-enhancements.js";
import { bootCodeEditors } from "./features/code-editors.js";
import { bootSecretGuidance } from "./features/secret-guidance.js";
import { bootTablerUi } from "./features/tabler-ui.js";

const LIBRARY_VALUE_CSS = "/static/css/v11-library-value.css";

function ensureLibraryValueStyles() {
  if (document.querySelector('link[data-devconsole-v11="library-value-css"]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = LIBRARY_VALUE_CSS;
  link.dataset.devconsoleV11 = "library-value-css";
  document.head.appendChild(link);
}

// Install the fetch observer while the module is evaluated, before the legacy
// DOMContentLoaded handlers issue their first Map/Activity/Infrastructure reads.
// It never changes a response; it only explains 403/missing-config states.
if (features.enabled("foundation")) bootReadFeedback();

async function bootFoundation() {
  document.documentElement.dataset.devconsoleUi = "v1.1";
  document.documentElement.classList.add("dc-v11-foundation");
  ensureLibraryValueStyles();

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

  // Tabler owns the visual language only on this experimental UX branch.
  // It is additive: legacy IDs, handlers, tabs and API contracts remain canonical.
  const tablerPromise = bootTablerUi();
  const environmentState = await bootMultiEnvironment();

  bootSecretGuidance();
  bootTerminalAddons();
  bootSplitLayouts();
  bootGridEnhancements();
  bootCodeEditors();
  await tablerPromise;

  events.emit("v11-ready", {
    version: api.version,
    features: features.snapshot(),
    environments: environmentState?.available || [],
    tabler: document.documentElement.dataset.dcTabler || "fallback",
  });
}

if (features.enabled("foundation")) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootFoundation, { once: true });
  } else {
    bootFoundation();
  }
}
