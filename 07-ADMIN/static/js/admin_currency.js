/** Currency admin — rates and conversion. */
const OrionAdminCurrency = {
  async loadRates() {
    const el = document.getElementById("currency-rates-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/currency/rates");
      const rows = data.rates || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد أسعار.', 'No rates found.'); return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          r.from_currency, " → ", r.to_currency, " = ", r.rate, " (", r.source || OrionI18n.t('يدوي', 'manual'), ")"
        ]));
      }
    } catch (err) {
      el.textContent = OrionI18n.t('تعذّر تحميل الأسعار. قد يقتصر التعديل على مسؤولي المنصة.', 'Failed to load rates. Editing may be restricted to platform admins.');
    }
  },

  init() {
    const form = document.getElementById("currency-rate-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/currency/rates", {
          from_currency: fd.get("from_currency"), to_currency: fd.get("to_currency"), rate: fd.get("rate"),
        });
        form.reset();
        OrionAdminCurrency.loadRates();
      });
    }
    const btn = document.getElementById("btn-convert");
    if (btn) {
      btn.addEventListener("click", async () => {
        const amount = document.getElementById("conv-amount").value;
        const from = document.getElementById("conv-from").value;
        const to = document.getElementById("conv-to").value;
        try {
          const data = await OrionAPI.get(`/currency/convert?amount=${amount}&from=${from}&to=${to}`);
          OrionUI.set("conv-result", `${data.result} ${to}`, "textContent");
        } catch (err) {
          document.getElementById("conv-result").textContent = OrionI18n.t('تعذّر التحويل. تحقّق من المبلغ والعملات.', 'Conversion failed. Check the amount and currencies.');
        }
      });
    }
    OrionAdminCurrency.loadRates();
  },
};