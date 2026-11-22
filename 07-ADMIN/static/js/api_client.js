/** Unified /api/v1 client for admin UIs — loading, errors, dedupe, timeout. */
const OrionAPI = {
  timeoutMs: 15000,
  _inflight: new Map(),

  getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  },

  headers() {
    const h = {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Locale": document.documentElement.lang || "ar",
    };
    const csrf = this.getCookie("csrf_access_token");
    if (csrf) h["X-CSRF-TOKEN"] = csrf;
    const tenantId = document.body.dataset.tenantId;
    if (tenantId) h["X-Tenant-ID"] = tenantId;
    return h;
  },

  normalizeError(data, status) {
    if (data && typeof data === "object") {
      const message = data.error || data.message || data.detail;
      if (message) return String(message);
    }
    return `طلب فشل (${status})`;
  },

  notifyError(error, path) {
    document.dispatchEvent(
      new CustomEvent("orion-api-error", { detail: { error, path } })
    );
  },

  async request(method, path, body, options = {}) {
    const key = `${method}:${path}:${body === undefined ? "" : JSON.stringify(body)}`;
    if (method === "GET" && this._inflight.has(key)) {
      return this._inflight.get(key);
    }

    const controller = new AbortController();
    const timer = setTimeout(
      () => controller.abort(),
      options.timeoutMs || this.timeoutMs
    );
    const opts = {
      method,
      headers: this.headers(),
      signal: controller.signal,
      credentials: "same-origin",
    };
    if (body !== undefined) opts.body = JSON.stringify(body);

    const task = (async () => {
      try {
        const res = await fetch(`/api/v1${path}`, opts);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const error = new Error(this.normalizeError(data, res.status));
          error.status = res.status;
          this.notifyError(error, path);
          throw error;
        }
        return data;
      } catch (error) {
        if (error.name === "AbortError") {
          const timeoutError = new Error("انتهت مهلة الطلب — حاول مرة أخرى");
          timeoutError.status = 408;
          this.notifyError(timeoutError, path);
          throw timeoutError;
        }
        if (!error.status) this.notifyError(error, path);
        throw error;
      } finally {
        clearTimeout(timer);
        this._inflight.delete(key);
      }
    })();

    if (method === "GET") this._inflight.set(key, task);
    return task;
  },

  get(path, options) { return this.request("GET", path, undefined, options); },
  post(path, body, options) { return this.request("POST", path, body, options); },
  put(path, body, options) { return this.request("PUT", path, body, options); },
  delete(path, options) { return this.request("DELETE", path, undefined, options); },
};
