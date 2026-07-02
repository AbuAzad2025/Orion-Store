/** Reconciliation v2 admin — runs and items. */
const OrionAdminReconciliation = {
  async loadRuns() {
    const el = document.getElementById("reconciliation-runs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/reconciliation/runs");
      const rows = data.runs || [];
      if (!rows.length) { el.textContent = "لا توجد تشغيلات."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2"><strong>${r.run_number}</strong> — ${r.status} — ${r.matched_count || 0}/${r.total_events || 0} متطابق</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const createBtn = document.getElementById("btn-create-run");
    if (createBtn) {
      createBtn.addEventListener("click", async () => {
        await OrionAPI.post("/reconciliation/runs");
        OrionAdminReconciliation.loadRuns();
      });
    }
    const itemForm = document.getElementById("reconciliation-item-form");
    if (itemForm) {
      itemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(itemForm);
        await OrionAPI.post(`/reconciliation/runs/${fd.get("run_id")}/items`, {
          financial_event_id: parseInt(fd.get("financial_event_id")),
          expected_amount: fd.get("expected_amount"), actual_amount: fd.get("actual_amount"),
        });
        itemForm.reset();
        alert("تم إضافة البند");
      });
    }
    OrionAdminReconciliation.loadRuns();
  },
};