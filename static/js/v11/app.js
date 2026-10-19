import { events } from "./core/events.js";
import { features } from "./core/features.js";
import { bootMultiEnvironment } from "./features/multi-env.js";
import { bootReadFeedback } from "./features/read-feedback.js";
import { bootTerminalAddons } from "./features/terminal-addons.js";
import { bootSplitLayouts } from "./features/split-layouts.js";
import { bootGridEnhancements } from "./features/grid-enhancements.js";
import { bootCodeEditors } from "./features/code-editors.js";

// Install the fetch observer while the module is evaluated, before the legacy
// DOMContentLoaded handlers issue their first Map/Activity/Infrastructure reads.
// It never changes a response; it only explains 403/missing-config states.
if (features.enabled("foundation")) bootReadFeedback();

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

  // The existing Consolas tab remains the canonical experience. Dockview is
  // kept vendored for future composition work but is no longer exposed as a
  // second/duplicate workspace. Improvements are applied in-place instead.
  bootTerminalAddons();
  bootSplitLayouts();
  bootGridEnhancements();
  bootCodeEditors();

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
