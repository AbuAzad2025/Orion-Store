/** Tenant admin page loaders (wave 5 #52-53). */
document.addEventListener("DOMContentLoaded", () => {
  const statsEl = document.getElementById("tenant-stats");
  if (statsEl) {
    OrionAPI.get("/tenant/dashboard")
      .then((data) => {
        const s = data.stats;
        statsEl.innerHTML = `
          <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">الطلبات</p><p class="text-2xl font-bold">${s.orders_total}</p></div>
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">مدفوعة</p><p class="text-2xl font-bold">${s.orders_paid}</p></div>
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">المنتجات</p><p class="text-2xl font-bold">${s.products_total}</p></div>
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">منشورة</p><p class="text-2xl font-bold">${s.products_published}</p></div>
          </div>`;
      })
      .catch((err) => {
        statsEl.textContent = err.message;
      });
  }

  const gatewaysEl = document.getElementById("gateways-list");
  if (gatewaysEl) {
    OrionAPI.get("/tenant/gateways")
      .then((data) => {
        if (!data.gateways.length) {
          gatewaysEl.innerHTML = "<p class='text-gray-500'>لا توجد بوابات.</p>";
          return;
        }
        gatewaysEl.innerHTML = data.gateways
          .map(
            (g) =>
              `<div class="rounded border p-3 mb-2"><strong>${g.display_name}</strong> (${g.provider}) — ${g.status}</div>`
          )
          .join("");
      })
      .catch((err) => {
        gatewaysEl.textContent = err.message;
      });
  }

  const codBtn = document.getElementById("enable-cod");
  if (codBtn) {
    codBtn.addEventListener("click", () => {
      OrionAPI.post("/tenant/gateways/cod")
        .then(() => location.reload())
        .catch((err) => alert(err.message));
    });
  }

  const templatesEl = document.getElementById("templates-list");
  if (templatesEl) {
    OrionAPI.get("/tenant/document-templates")
      .then((data) => {
        if (!data.templates.length) {
          templatesEl.innerHTML = "<p class='text-gray-500'>لا توجد قوالب بعد.</p>";
          return;
        }
        templatesEl.innerHTML = data.templates
          .map(
            (t) =>
              `<div class="rounded border p-3 mb-2"><strong>${t.document_type}</strong> (${t.locale})</div>`
          )
          .join("");
      })
      .catch((err) => {
        templatesEl.textContent = err.message;
      });
  }

  const saveBtn = document.getElementById("save-invoice-template");
  if (saveBtn) {
    saveBtn.addEventListener("click", () => {
      const body = document.getElementById("invoice-body").value;
      OrionAPI.put("/tenant/document-templates/invoice", { body_html: body })
        .then(() => alert("تم الحفظ"))
        .catch((err) => alert(err.message));
    });
  }
});
