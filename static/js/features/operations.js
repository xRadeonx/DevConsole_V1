export function createOperationsFeature(api, events) {
  return {
    async buildJobs() {
      const result = await api.get('/api/v1.1/build/jobs');
      events.emit('builds:jobs', result);
      return result;
    },
    async startBuild(payload) {
      const result = await api.post('/api/v1.1/build/start', payload);
      events.emit('builds:started', result);
      return result;
    },
    async cancelBuild(jobId) {
      const result = await api.post('/api/v1.1/build/cancel', { job_id: jobId });
      events.emit('builds:cancelled', result);
      return result;
    },
    async k8sPreflight(env = 'develop', context = '') {
      const qs = new URLSearchParams({ env });
      if (context) qs.set('context', context);
      return api.get(`/api/v1.1/k8s/preflight?${qs}`);
    },
    async previewManifest({ service, env = 'develop', version }) {
      const qs = new URLSearchParams({ service, env, version });
      return api.get(`/api/v1.1/k8s/manifest_preview?${qs}`);
    },
    updateImage(payload) { return api.post('/api/v1.1/k8s/update_image', payload); },
    applyManifest(payload) { return api.post('/api/v1.1/k8s/apply', payload); },
    rollback(payload) { return api.post('/api/v1.1/k8s/rollback', payload); },
  };
}
