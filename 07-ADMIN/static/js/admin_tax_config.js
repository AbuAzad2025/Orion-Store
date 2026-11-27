/** Tenant tax settings: rate and whether displayed prices include tax. */
const OrionAdminTaxConfig = {
  async load() {
    const form = document.getElementById("tax-config-form");
    if (!form) return;
    try {
      const data = await OrionAPI.get("/tenant/tax-config");
      form.querySelector('[name="tax_rate"]').value = data.tax_config.tax_rate;
      form.querySelector('[name="tax_included"]').checked = data.tax_config.tax_included;
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
