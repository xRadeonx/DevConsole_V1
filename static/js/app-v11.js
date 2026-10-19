import { ApiClient } from './modules/api-client.js';
import { EventBus } from './modules/event-bus.js';
import { enhanceTerminal, loadTerminalAddons } from './modules/terminal-enhancements.js';

const api = new ApiClient();
const events = new EventBus();

const DevConsoleV11 = {
  api,
  events,
  terminal: { enhanceTerminal, loadTerminalAddons },
  capabilities: null,
  async refreshCapabilities() {
    try {
      this.capabilities = await api.get('/api/v1.1/capabilities');
      document.documentElement.dataset.devconsoleV11 = 'ready';
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
