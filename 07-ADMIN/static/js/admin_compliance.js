/** Compliance admin — consent, DSR, cookies, SSO. */
const OrionAdminCompliance = {
  async loadConsent() {
    const el = document.getElementById("consent-records-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/consent");
      const rows = data.consent_records || [];
      if (!rows.length) { el.textContent = "لا توجد سجلات."; return; }
      SafeDOM.clear(el);
      for (const c of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          c.customer_email, " — ", c.consent_type, " — ", c.granted ? "ممنوحة" : "ملغاة"
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadDSR() {
    const el = document.getElementById("dsr-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/data-requests");
      const rows = data.requests || [];
      if (!rows.length) { el.textContent = "لا توجد طلبات."; return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          r.customer_email, " — ", r.request_type, " — ", r.status || "pending"
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadCookieSettings() {
    const el = document.getElementById("cookie-settings-display");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/cookie-settings");
      const s = data.settings;
      if (!s) { el.textContent = "لا توجد إعدادات."; return; }
      SafeDOM.clear(el);
      el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
        s.banner_message || "بدون نص", " — ", s.is_active ? "مفعّل" : "معطّل"
      ]));
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadSSO() {
    const el = document.getElementById("sso-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/sso");
      const rows = data.sso_providers || [];
      if (!rows.length) { el.textContent = "لا توجد مزودين."; return; }
      SafeDOM.clear(el);
      for (const p of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          p.provider_type, " — ", p.issuer_url || "بدون issuer"
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async ssoExchange(providerCode, externalEmail, tenantId) {
    return OrionAPI.post("/auth/sso/exchange", {
      provider_code: providerCode,
      external_email: externalEmail,
      tenant_id: tenantId || document.body.dataset.tenantId || undefined,
    });
  },

  init() {
    const consentForm = document.getElementById("consent-form");
    if (consentForm) {
      consentForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(consentForm);
        await OrionAPI.post("/compliance/consent", {
          customer_email: fd.get("customer_email"), consent_type: fd.get("consent_type"),
          granted: fd.get("granted") === "on",
        });
        consentForm.reset();
        OrionAdminCompliance.loadConsent();
      });
    }
    const dsrForm = document.getElementById("dsr-form");
    if (dsrForm) {
      dsrForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(dsrForm);
        await OrionAPI.post("/compliance/data-requests", {
          customer_email: fd.get("customer_email"), request_type: fd.get("request_type"),
        });
        dsrForm.reset();
        OrionAdminCompliance.loadDSR();
      });
    }
    const cookieForm = document.getElementById("cookie-form");
    if (cookieForm) {
      cookieForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(cookieForm);
        await OrionAPI.put("/compliance/cookie-settings", {
          banner_message: fd.get("banner_message") || undefined, is_active: fd.get("is_active") === "on",
        });
        OrionAdminCompliance.loadCookieSettings();
      });
    }
    const ssoForm = document.getElementById("sso-form");
    if (ssoForm) {
      ssoForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(ssoForm);
        await OrionAPI.post("/compliance/sso", {
          provider_type: fd.get("provider_type"), client_id: fd.get("client_id"),
          client_secret: fd.get("client_secret"), issuer_url: fd.get("issuer_url") || undefined,
        });
        ssoForm.reset();
        OrionAdminCompliance.loadSSO();
      });
    }
    const ssoExchangeForm = document.getElementById("sso-exchange-form");
    if (ssoExchangeForm) {
      ssoExchangeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(ssoExchangeForm);
        const result = await OrionAdminCompliance.ssoExchange(
          fd.get("provider_code"), fd.get("external_email"), fd.get("tenant_id")
        );
        const out = document.getElementById("sso-exchange-result");
        if (out) {
          SafeDOM.clear(out);
          out.appendChild(SafeDOM.elem("span", {}, [
            result && result.user ? result.user.email : "تم تسجيل الدخول"
          ]));
        }
        ssoExchangeForm.reset();
      });
    }
    OrionAdminCompliance.loadConsent();
    OrionAdminCompliance.loadDSR();
    OrionAdminCompliance.loadCookieSettings();
    OrionAdminCompliance.loadSSO();
  },
};