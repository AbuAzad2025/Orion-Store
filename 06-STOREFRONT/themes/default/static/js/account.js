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
    await this.loadServices();
  },
  notify(message, kind) {
    let el = document.getElementById("account-notice");
    if (!el) {
      el = document.createElement("p");
      el.id = "account-notice";
      el.setAttribute("role", "status");
      document.getElementById("account-user")?.prepend(el);
    }
    el.textContent = message;
    el.className = kind === "error" ? "text-red-600 text-sm" : "orion-muted text-sm";
  },

  async loadServices() {
    const creditEl = document.getElementById("account-credit");
    if (!creditEl) return;
    try {
      const [credit, plans, quotes, registries] = await Promise.all([
        this.api("GET", "/credit"),
        this.api("GET", "/plans"),
        this.api("GET", "/quote-requests"),
        this.api("GET", "/gift-registries"),
      ]);
      creditEl.textContent = `رصيد المتجر: ${credit.data.credit?.balance || "0.00"}`;
      const plansEl = document.getElementById("account-plans");
      if (plansEl) {
        SafeDOM.clear(plansEl);
        const rows = plans.data.plans || [];
        if (!rows.length) plansEl.textContent = "لا توجد خطط متاحة.";
        for (const p of rows) {
          plansEl.appendChild(SafeDOM.elem("div", { className: "border-b py-1 flex items-center justify-between" }, [
            SafeDOM.elem("span", {}, [`${p.name} — ${p.price} ${p.currency || ""}`]),
            SafeDOM.actionBtn("اشترك", "text-blue-700 text-xs", async () => {
              try {
                await this.api("POST", "/subscribe", { plan_id: p.id });
                this.notify("تم الاشتراك", "success");
              } catch (err) { this.notify(err.message, "error"); }
            }),
          ]));
        }
      }
      const quotesEl = document.getElementById("account-quotes");
      if (quotesEl) {
        SafeDOM.clear(quotesEl);
        for (const q of quotes.data.quotes || []) {
          quotesEl.appendChild(SafeDOM.elem("div", { className: "border-b py-1" }, [`${q.quote_number} — ${q.status}`]));
        }
      }
      const regsEl = document.getElementById("account-registries");
      if (regsEl) {
        SafeDOM.clear(regsEl);
        for (const r of registries.data.registries || []) {
          regsEl.appendChild(SafeDOM.elem("div", { className: "border-b py-1" }, [`${r.registry_name} — ${r.slug}`]));
        }
      }
    } catch (err) { creditEl.textContent = err.message; }
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
    document.getElementById("quote-request-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        const body = { notes: fd.get("notes") || undefined };
        if (fd.get("product_id")) {
          body.product_id = Number(fd.get("product_id"));
          body.quantity = Number(fd.get("quantity") || 1);
        }
        await this.api("POST", "/quote-requests", body);
        e.target.reset();
        this.notify("تم إرسال طلب العرض", "success");
        this.loadServices();
      } catch (err) { this.notify(err.message, "error"); }
    });
    document.getElementById("gift-registry-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await this.api("POST", "/gift-registries", {
          registry_name: fd.get("registry_name"),
          event_type: fd.get("event_type") || undefined,
          event_date: fd.get("event_date") || undefined,
        });
        e.target.reset();
        this.notify("تم إنشاء القائمة", "success");
        this.loadServices();
      } catch (err) { this.notify(err.message, "error"); }
    });
    document.getElementById("gift-item-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await this.api("POST", `/gift-registries/${encodeURIComponent(fd.get("slug"))}/items`, {
          product_id: Number(fd.get("product_id")),
        });
        e.target.reset();
        this.notify("تمت إضافة المنتج", "success");
        this.loadServices();
      } catch (err) { this.notify(err.message, "error"); }
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
