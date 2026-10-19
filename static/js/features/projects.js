export function createProjectsFeature(api, events) {
  let cache = null;
  return {
    async list({ refresh = false } = {}) {
      if (cache && !refresh) return cache;
      cache = await api.get('/api/v1.1/projects');
      events.emit('projects:loaded', cache);
      return cache;
    },
    clear() { cache = null; },
  };
}
