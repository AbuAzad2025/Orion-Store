/** Storefront customer account — JWT cookie (wave 15). */
const AccountUI = {
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
  async api(method, path, body) {
    const opts = { method, headers: this.headers() };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(`/api/v1/store/account${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok && res.status !== 401) throw new Error(data.error || res.statusText);
    return { ok: res.ok, status: res.status, data };
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
    const { ok, data } = await this.api("GET", "/me");
    if (!ok) {
      guest?.classList.remove("hidden");
      user?.classList.add("hidden");
      return;
    }
    guest?.classList.add("hidden");
    user?.classList.remove("hidden");
    const emailEl = document.getElementById("account-email");
    if (emailEl) emailEl.textContent = data.user.email;
    const orders = await this.api("GET", "/orders");
    const list = document.getElementById("account-orders");
    if (list) {
      const rows = orders.data.orders || [];
      SafeDOM.clear(list);
      if (rows.length) {
        rows.forEach((o) => {
          list.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [`${o.order_number} — ${o.total}`]));
        });
      } else {
        list.appendChild(SafeDOM.elem("p", { className: "text-gray-500" }, ["لا توجد طلبات."]));
      }
    }
  },
  init() {
    document.getElementById("login-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      this.showError("");
      const fd = new FormData(e.target);
      const { ok, data } = await this.api("POST", "/login", {
        email: fd.get("email"),
        password: fd.get("password"),
      });
      if (!ok) { this.showError(data.error); return; }
      this.loadProfile();
    });
    document.getElementById("register-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      this.showError("");
      const fd = new FormData(e.target);
      const { ok, data } = await this.api("POST", "/register", {
        email: fd.get("email"),
        password: fd.get("password"),
        first_name: fd.get("first_name"),
      });
      if (!ok) { this.showError(data.error); return; }
      this.loadProfile();
    });
    const gdpr = async (type) => {
      const msg = document.getElementById("gdpr-msg");
      try {
        const { data } = await this.api("POST", "/data-requests", { request_type: type });
        const req = data.request;
        if (type === "export") {
          const payload = await this.api("GET", `/data-requests/${req.id}/export`);
          const blob = new Blob([JSON.stringify(payload.data, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url; a.download = "orion-my-data.json"; a.click();
          URL.revokeObjectURL(url);
          msg.textContent = "تم تنزيل نسخة بياناتك.";
        } else {
          if (!window.confirm("سيتم إخفاء بياناتك الشخصية نهائياً. متابعة؟")) return;
          await this.api("POST", `/data-requests/${req.id}/delete`, {});
          msg.textContent = "تم تنفيذ طلب الحذف.";
          this.loadProfile();
        }
      } catch (err) { msg.textContent = err.message; }
    };
    document.getElementById("gdpr-export-btn")?.addEventListener("click", () => gdpr("export"));
    document.getElementById("gdpr-delete-btn")?.addEventListener("click", () => gdpr("delete"));
    document.getElementById("logout-btn")?.addEventListener("click", async () => {
      await fetch("/api/v1/store/account/logout", { method: "POST", headers: this.headers() });
      this.loadProfile();
    });
    this.loadProfile();
  },
};
document.addEventListener("DOMContentLoaded", () => AccountUI.init());
