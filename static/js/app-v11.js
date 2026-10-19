import { ApiClient } from './modules/api-client.js';
import { EventBus } from './modules/event-bus.js';
import { enhanceTerminal, loadTerminalAddons } from './modules/terminal-enhancements.js';
import { createProjectsFeature } from './features/projects.js';
import { createOperationsFeature } from './features/operations.js';

const api = new ApiClient();
const events = new EventBus();
const projects = createProjectsFeature(api, events);
const operations = createOperationsFeature(api, events);

const DevConsoleV11 = {
  api,
  events,
  projects,
  operations,
  terminal: { enhanceTerminal, loadTerminalAddons },
  capabilities: null,
  get role() { return this.capabilities?.role || 'viewer'; },
  async refreshCapabilities() {
    try {
      this.capabilities = await api.get('/api/v1.1/capabilities');
      document.documentElement.dataset.devconsoleV11 = 'ready';
      document.documentElement.dataset.devconsoleRole = this.role;
      events.emit('v11:capabilities', this.capabilities);
      return this.capabilities;
    } catch (error) {
      document.documentElement.dataset.devconsoleV11 = 'degraded';
      events.emit('v11:error', { error });
      return null;
    }
  },
};

window.DevConsoleV11 = DevConsoleV11;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => DevConsoleV11.refreshCapabilities(), { once: true });
} else {
  DevConsoleV11.refreshCapabilities();
}
