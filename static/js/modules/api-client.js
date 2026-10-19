export class ApiClient {
  constructor(base = '') { this.base = base; }

  async request(path, options = {}) {
    const response = await fetch(`${this.base}${path}`, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const text = await response.text();
    let payload;
    try { payload = text ? JSON.parse(text) : {}; }
    catch { payload = { success: false, message: text || `HTTP ${response.status}` }; }
    if (!response.ok) {
      const error = new Error(payload.message || `HTTP ${response.status}`);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  get(path) { return this.request(path); }
  post(path, payload = {}) {
    return this.request(path, { method: 'POST', body: JSON.stringify(payload) });
  }
}
