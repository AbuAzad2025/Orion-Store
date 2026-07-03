/** Platform admin page loaders (wave 5 #54). */
document.addEventListener("DOMContentLoaded", () => {
  const tenantsEl = document.getElementById("platform-tenants");
  if (tenantsEl) {
    OrionAPI.get("/tenants/")
      .then((data) => {
        SafeDOM.clear(tenantsEl);
        data.tenants.forEach((t) => {
          const link = SafeDOM.elem("a", { className: "text-blue-600", href: `/admin/platform/stores/${t.id}/finance` }, ["مالية"]);
          tenantsEl.appendChild(SafeDOM.elem("tr", { className: "border-b" }, [
            SafeDOM.elem("td", { className: "py-2" }, [t.name]),
            SafeDOM.elem("td", { className: "py-2" }, [t.slug]),
            SafeDOM.elem("td", { className: "py-2" }, [link])
          ]));
        });
      })
      .catch((err) => {
        SafeDOM.clear(tenantsEl);
        tenantsEl.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { colspan: "3" }, [err.message])
        ]));
      });
  }

  const reportEl = document.getElementById("financial-report");
  const tenantId = document.body.dataset.reportTenantId;
  if (reportEl && tenantId) {
    OrionAPI.get(`/platform/stores/${tenantId}/financial-report`)
      .then((data) => {
        const s = data.summary;
        SafeDOM.clear(reportEl);
        reportEl.appendChild(SafeDOM.elem("h2", { className: "text-xl font-bold mb-4" }, [data.tenant.name]));
        const cards = [
          SafeDOM.elem("div", { className: "rounded bg-white p-4 shadow" }, [
            SafeDOM.elem("p", { className: "text-sm text-gray-500" }, ["إجمالي الوارد"]),
            SafeDOM.elem("p", { className: "text-xl font-bold" }, [s.total_inbound])
          ]),
          SafeDOM.elem("div", { className: "rounded bg-white p-4 shadow" }, [
            SafeDOM.elem("p", { className: "text-sm text-gray-500" }, ["العمولة"]),
            SafeDOM.elem("p", { className: "text-xl font-bold" }, [s.total_commission])
          ]),
          SafeDOM.elem("div", { className: "rounded bg-white p-4 shadow" }, [
            SafeDOM.elem("p", { className: "text-sm text-gray-500" }, ["طلبات مدفوعة"]),
            SafeDOM.elem("p", { className: "text-xl font-bold" }, [s.orders_paid])
          ])
        ];
        reportEl.appendChild(SafeDOM.elem("div", { className: "grid grid-cols-2 gap-4 md:grid-cols-3 mb-6" }, cards));
        reportEl.appendChild(SafeDOM.elem("h3", { className: "font-semibold mb-2" }, ["أحداث مالية حديثة"]));
        const events = data.recent_events.map((e) => SafeDOM.elem("li", null, [`${e.event_type}: ${e.amount} ${e.currency}`]));
        reportEl.appendChild(SafeDOM.elem("ul", { className: "space-y-1 text-sm" }, events));
      })
      .catch((err) => {
        reportEl.textContent = err.message;
      });
  }

  const reconEl = document.getElementById("reconciliation-status");
  if (reconEl) {
    OrionAPI.get("/platform/reconciliation")
      .then((data) => {
        SafeDOM.clear(reconEl);
        const reconCards = [
          SafeDOM.elem("div", { className: "rounded bg-white p-4 shadow" }, [
            SafeDOM.elem("p", { className: "text-sm text-gray-500" }, ["عمولات معلقة"]),
            SafeDOM.elem("p", { className: "text-xl font-bold" }, [data.pending_commission_entries])
          ]),
          SafeDOM.elem("div", { className: "rounded bg-white p-4 shadow" }, [
            SafeDOM.elem("p", { className: "text-sm text-gray-500" }, ["عمولات مسوّاة"]),
            SafeDOM.elem("p", { className: "text-xl font-bold" }, [data.settled_commission_entries])
          ]),
          SafeDOM.elem("div", { className: "rounded bg-white p-4 shadow" }, [
            SafeDOM.elem("p", { className: "text-sm text-gray-500" }, ["أحداث مالية"]),
            SafeDOM.elem("p", { className: "text-xl font-bold" }, [data.financial_events_total])
          ])
        ];
        reconEl.appendChild(SafeDOM.elem("div", { className: "grid grid-cols-3 gap-4" }, reconCards));
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
