/** Reconciliation v2 admin — runs and items. */
const OrionAdminReconciliation = {
  async loadRuns() {
    const el = document.getElementById("reconciliation-runs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/reconciliation/runs");
      const rows = data.runs || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد تشغيلات.', 'No runs.'); return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        const children = [
          SafeDOM.elem("span", {}, [
            SafeDOM.elem("strong", {}, [r.run_number]),
            " — ", r.status, " — ", r.matched_count || 0, "/", r.total_events || 0, " " + OrionI18n.t('متطابق', 'matched')
          ])
        ];
        if (r.status === "pending" || r.status === "draft") {
          children.push(SafeDOM.actionBtn(OrionI18n.t('إكمال', 'Complete'), "orion-btn", async () => {
            try {
              await OrionAPI.post(`/reconciliation/runs/${r.id}/complete`);
              OrionUI.toast(OrionI18n.t('تم إكمال التسوية', 'Reconciliation completed'), "success");
              OrionAdminReconciliation.loadRuns();
            } catch (err) { OrionUI.toast(err.message, "error"); }
          }));
        }
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex items-center justify-between" }, children));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  init() {
    const createBtn = document.getElementById("btn-create-run");
    if (createBtn) {
      createBtn.addEventListener("click", async () => {
        try {
          await OrionAPI.post("/reconciliation/runs");
          OrionAdminReconciliation.loadRuns();
        } catch (err) { OrionUI.toast(err.message, "error"); }
      });
    }
    const itemForm = document.getElementById("reconciliation-item-form");
    if (itemForm) {
      itemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(itemForm);
        try {
          await OrionAPI.post(`/reconciliation/runs/${fd.get("run_id")}/items`, {
            financial_event_id: parseInt(fd.get("financial_event_id")),
            expected_amount: fd.get("expected_amount"), actual_amount: fd.get("actual_amount"),
          });
          itemForm.reset();
          OrionUI.toast(OrionI18n.t('تم إضافة البند', 'Item added'), "success");
        } catch (err) { OrionUI.toast(err.message, "error"); }
      });
    }
    OrionAdminReconciliation.loadRuns();
  },
};