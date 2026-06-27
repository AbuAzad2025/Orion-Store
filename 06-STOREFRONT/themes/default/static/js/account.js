/** Storefront customer account — JWT (wave 15). */
const AccountUI = {
  tokenKey: "orion_customer_token",
  get token() {
    return localStorage.getItem(this.tokenKey) || "";
  },
  setToken(value) {
    if (value) localStorage.setItem(this.tokenKey, value);
    else localStorage.removeItem(this.tokenKey);
  },
  headers() {
    const h = { "Content-Type": "application/json" };
    if (this.token) h.Authorization = `Bearer ${this.token}`;
    const tenantId = document.body.dataset.tenantId;
    if (tenantId) h["X-Tenant-ID"] = tenantId;
    return h;
  },
  async api(method, path, body) {
    const opts = { method, headers: this.headers() };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(`/api/v1/store/account${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  },
  showError(msg) {
    const el = document.getElementById("account-error");
    if (!el) return;
    el.textContent = msg;
    el.classList.toggle("hidden", !msg);
  },
  async loadProfile() {
    const guest = document.getElementById("account-guest");
    const user = document.getElementById("account-user");
    if (!this.token) {
      guest?.classList.remove("hidden");
      user?.classList.add("hidden");
      return;
    }
    try {
      const data = await this.api("GET", "/me");
      guest?.classList.add("hidden");
      user?.classList.remove("hidden");
      const emailEl = document.getElementById("account-email");
      if (emailEl) emailEl.textContent = data.user.email;
      const orders = await this.api("GET", "/orders");
      const list = document.getElementById("account-orders");
      if (list) {
        const rows = orders.orders || [];
        list.innerHTML = rows.length
          ? rows
              .map((o) => `<div class="border-b py-2">${o.order_number} — ${o.total}</div>`)
              .join("")
          : "لا توجد طلبات.";
      }
    } catch (err) {
      this.setToken("");
      this.loadProfile();
    }
  },
  init() {
    document.getElementById("login-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      this.showError("");
      const fd = new FormData(e.target);
      try {
        const data = await this.api("POST", "/login", {
          email: fd.get("email"),
          password: fd.get("password"),
        });
        this.setToken(data.access_token);
        this.loadProfile();
      } catch (err) {
        this.showError(err.message);
      }
    });
    document.getElementById("register-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      this.showError("");
      const fd = new FormData(e.target);
      try {
        const data = await this.api("POST", "/register", {
          email: fd.get("email"),
          password: fd.get("password"),
          first_name: fd.get("first_name"),
        });
        this.setToken(data.access_token);
        this.loadProfile();
      } catch (err) {
        this.showError(err.message);
      }
    });
    document.getElementById("logout-btn")?.addEventListener("click", () => {
      this.setToken("");
      this.loadProfile();
    });
    this.loadProfile();
  },
};
document.addEventListener("DOMContentLoaded", () => AccountUI.init());
