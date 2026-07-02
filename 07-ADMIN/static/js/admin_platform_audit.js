/** Platform Audit admin — reports and logs (platform_admin only). */
const OrionAdminPlatformAudit = {
  async loadReports() {
    const el = document.getElementById("audit-reports-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/audit/reports");
      const rows = data.reports || [];
      if (!rows.length) { el.textContent = "لا توجد تقارير."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2"><strong>${r.report_number}</strong> — ${r.report_type} — بواسطة #${r.generated_by}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadLogs() {
    const el = document.getElementById("admin-logs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/audit/logs");
      const rows = data.logs || [];
      if (!rows.length) { el.textContent = "لا توجد سجلات."; return; }
      el.innerHTML = rows.map((l) =>
        `<div class="border-b py-2">#${l.user_id} — ${l.action}${l.target_type ? ` → ${l.target_type}#${l.target_id}` : ""}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    OrionAdminPlatformAudit.loadReports();
    OrionAdminPlatformAudit.loadLogs();
  },
};