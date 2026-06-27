/** Unified /api/v1 client for admin UIs (wave 5 #50). */
const OrionAPI = {
  get token() {
    return localStorage.getItem("orion_access_token") || "";
  },
  setToken(value) {
    if (value) localStorage.setItem("orion_access_token", value);
    else localStorage.removeItem("orion_access_token");
  },
  headers() {
    const h = { "Content-Type": "application/json" };
    if (this.token) h.Authorization = `Bearer ${this.token}`;
    const tenantId = document.body.dataset.tenantId;
    if (tenantId) h["X-Tenant-ID"] = tenantId;
    const userId = document.body.dataset.userId;
    if (userId) h["X-User-ID"] = userId;
    return h;
  },
  async request(method, path, body) {
    const opts = { method, headers: this.headers() };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(`/api/v1${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  },
  get(path) {
    return this.request("GET", path);
  },
  post(path, body) {
    return this.request("POST", path, body);
  },
  put(path, body) {
    return this.request("PUT", path, body);
  },
};
