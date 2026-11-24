/** Compliance admin — consent, DSR, cookies, SSO. */
const OrionAdminCompliance = {
  async loadConsent() {
    const el = document.getElementById("consent-records-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/consent");
      const rows = data.consent_records || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد سجلات.', 'No records.'); return; }
      SafeDOM.clear(el);
      for (const c of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          c.customer_email, " — ", c.consent_type, " — ", c.granted ? OrionI18n.t('ممنوحة', 'Granted') : OrionI18n.t('ملغاة', 'Revoked')
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadDSR() {
    const el = document.getElementById("dsr-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/data-requests");
      const rows = data.data_requests || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد طلبات.', 'No requests.'); return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        const actions = SafeDOM.elem("span", { className: "inline-flex gap-2 ms-3" }, []);
        if (["export", "delete", "rectify"].includes(r.request_type) && r.status !== "completed") {
          const url = r.request_type === "export" ? "export"
            : r.request_type === "delete" ? "execute-delete" : "rectify";
          const label = r.request_type === "export" ? OrionI18n.t('تصدير', 'Export')
            : r.request_type === "delete" ? OrionI18n.t('تنفيذ الحذف', 'Execute deletion') : OrionI18n.t('تنفيذ التصحيح', 'Execute rectification');
          actions.appendChild(SafeDOM.actionBtn(label, "orion-btn", async () => {
            try {
              await OrionAPI.post(`/compliance/data-requests/${r.id}/${url}`);
              OrionUI.toast(OrionI18n.t('تم تنفيذ الطلب', 'Request executed'), "success");
              OrionAdminCompliance.loadDSR();
            } catch (err) { OrionUI.toast(err.message, "error"); }
          }));
        }
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex items-center" }, [
          SafeDOM.elem("span", {}, [r.customer_email, " — ", r.request_type, " — ", r.status || "pending"]),
          actions
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadCookieSettings() {
    const el = document.getElementById("cookie-settings-display");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/cookie-settings");
      const s = data.cookie_settings;
      if (!s) { el.textContent = OrionI18n.t('لا توجد إعدادات.', 'No settings.'); return; }
      SafeDOM.clear(el);
      el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
        s.banner_message || OrionI18n.t('بدون نص', 'No text'), " — ", s.is_active ? OrionI18n.t('مفعّل', 'Active') : OrionI18n.t('معطّل', 'Disabled')
      ]));
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadSSO() {
    const el = document.getElementById("sso-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/compliance/sso");
      const rows = data.sso_providers || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد مزودين.', 'No providers.'); return; }
      SafeDOM.clear(el);
      for (const p of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          p.provider_type, " — ", p.issuer_url || OrionI18n.t('بدون issuer', 'No issuer')
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
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
            result && result.user ? result.user.email : OrionI18n.t('تم تسجيل الدخول', 'Logged in')
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