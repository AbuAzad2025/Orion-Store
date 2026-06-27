/** Platform admin page loaders (wave 5 #54). */
document.addEventListener("DOMContentLoaded", () => {
  const tenantsEl = document.getElementById("platform-tenants");
  if (tenantsEl) {
    OrionAPI.get("/tenants/")
      .then((data) => {
        tenantsEl.innerHTML = data.tenants
          .map(
            (t) =>
              `<tr class="border-b">
                <td class="py-2">${t.name}</td>
                <td class="py-2">${t.slug}</td>
                <td class="py-2"><a class="text-blue-600" href="/admin/platform/stores/${t.id}/finance">مالية</a></td>
              </tr>`
          )
          .join("");
      })
      .catch((err) => {
        tenantsEl.innerHTML = `<tr><td colspan="3">${err.message}</td></tr>`;
      });
  }

  const reportEl = document.getElementById("financial-report");
  const tenantId = document.body.dataset.reportTenantId;
  if (reportEl && tenantId) {
    OrionAPI.get(`/platform/stores/${tenantId}/financial-report`)
      .then((data) => {
        const s = data.summary;
        reportEl.innerHTML = `
          <h2 class="text-xl font-bold mb-4">${data.tenant.name}</h2>
          <div class="grid grid-cols-2 gap-4 md:grid-cols-3 mb-6">
            <div class="rounded bg-white p-4 shadow"><p class="text-sm text-gray-500">إجمالي الوارد</p><p class="text-xl font-bold">${s.total_inbound}</p></div>
            <div class="rounded bg-white p-4 shadow"><p class="text-sm text-gray-500">العمولة</p><p class="text-xl font-bold">${s.total_commission}</p></div>
            <div class="rounded bg-white p-4 shadow"><p class="text-sm text-gray-500">طلبات مدفوعة</p><p class="text-xl font-bold">${s.orders_paid}</p></div>
          </div>
          <h3 class="font-semibold mb-2">أحداث مالية حديثة</h3>
          <ul class="space-y-1 text-sm">${data.recent_events
            .map((e) => `<li>${e.event_type}: ${e.amount} ${e.currency}</li>`)
            .join("")}</ul>`;
      })
      .catch((err) => {
        reportEl.textContent = err.message;
      });
  }

  const reconEl = document.getElementById("reconciliation-status");
  if (reconEl) {
    OrionAPI.get("/platform/reconciliation")
      .then((data) => {
        reconEl.innerHTML = `
          <div class="grid grid-cols-3 gap-4">
            <div class="rounded bg-white p-4 shadow"><p class="text-sm text-gray-500">عمولات معلقة</p><p class="text-xl font-bold">${data.pending_commission_entries}</p></div>
            <div class="rounded bg-white p-4 shadow"><p class="text-sm text-gray-500">عمولات مسوّاة</p><p class="text-xl font-bold">${data.settled_commission_entries}</p></div>
            <div class="rounded bg-white p-4 shadow"><p class="text-sm text-gray-500">أحداث مالية</p><p class="text-xl font-bold">${data.financial_events_total}</p></div>
          </div>`;
      })
      .catch((err) => {
        reconEl.textContent = err.message;
      });
  }

  const runBtn = document.getElementById("run-reconciliation");
  if (runBtn) {
    runBtn.addEventListener("click", () => {
      OrionAPI.post("/platform/reconciliation/run", {})
        .then(() => location.reload())
        .catch((err) => alert(err.message));
    });
  }
});
