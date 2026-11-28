/** Tenant tax settings: rate and whether displayed prices include tax. */
const OrionAdminTaxConfig = {
  async load() {
    const form = document.getElementById("tax-config-form");
    if (!form) return;
    try {
      const data = await OrionAPI.get("/tenant/tax-config");
      const cfg = data.tax_config;
      if (!cfg) return;
      const rate = form.querySelector('[name="tax_rate"]');
      if (rate) rate.value = cfg.tax_rate ?? "";
      const included = form.querySelector('[name="tax_included"]');
      if (included) included.checked = Boolean(cfg.tax_included);
    } catch (err) { /* keep defaults */ }
  },
  init() {
    const form = document.getElementById("tax-config-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const msg = document.getElementById("tax-config-msg");
        try {
          await OrionAPI.put("/tenant/tax-config", {
            tax_rate: fd.get("tax_rate"),
            tax_included: fd.get("tax_included") === "on",
          });
          if (msg) msg.textContent = OrionI18n.t("تم حفظ الإعدادات", "Settings saved");
          OrionUI.toast(OrionI18n.t("تم حفظ إعدادات الضريبة", "Tax settings saved"), "success");
        } catch (err) {
          if (msg) msg.textContent = err.message;
        }
      });
    }
    this.load();
  },
};
