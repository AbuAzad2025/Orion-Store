/** Currency admin — rates and conversion. */
const OrionAdminCurrency = {
  async loadRates() {
    const el = document.getElementById("currency-rates-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/currency/rates");
      const rows = data.rates || [];
      if (!rows.length) { el.textContent = "لا توجد أسعار."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2">${r.from_currency} → ${r.to_currency} = ${r.rate} (${r.source || "manual"})</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
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
        const data = await OrionAPI.get(`/currency/convert?amount=${amount}&from=${from}&to=${to}`);
        document.getElementById("conv-result").textContent = `${data.result} ${to}`;
      });
    }
    OrionAdminCurrency.loadRates();
  },
};