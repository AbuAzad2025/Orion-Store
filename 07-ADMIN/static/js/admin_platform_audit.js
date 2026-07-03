/** Platform Audit admin — reports and logs (platform_admin only). */
const OrionAdminPlatformAudit = {
  async loadReports() {
    const el = document.getElementById("audit-reports-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/audit/reports");
      const rows = data.reports || [];
      if (!rows.length) { el.textContent = "لا توجد تقارير."; return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [r.report_number]),
          " — ", r.report_type, " — بواسطة #", r.generated_by
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadLogs() {
    const el = document.getElementById("admin-logs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/audit/logs");
      const rows = data.logs || [];
      if (!rows.length) { el.textContent = "لا توجد سجلات."; return; }
      SafeDOM.clear(el);
      for (const l of rows) {
        const children = ["#", l.user_id, " — ", l.action];
        if (l.target_type) {
          children.push(" → ", l.target_type, "#", l.target_id);
        }
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, children));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    OrionAdminPlatformAudit.loadReports();
    OrionAdminPlatformAudit.loadLogs();
  },
};