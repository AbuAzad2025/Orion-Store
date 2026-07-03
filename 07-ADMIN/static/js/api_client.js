/** Unified /api/v1 client for admin UIs (wave 5 #50). */
const OrionAPI = {
  getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  },
  headers() {
    const h = { "Content-Type": "application/json" };
    const csrf = this.getCookie("csrf_access_token");
    if (csrf) h["X-CSRF-TOKEN"] = csrf;
    const tenantId = document.body.dataset.tenantId;
    if (tenantId) h["X-Tenant-ID"] = tenantId;
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
  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  put(path, body) { return this.request("PUT", path, body); },
  delete(path) { return this.request("DELETE", path); },
};
