/** Accessibility admin — audit logger. */
const OrionAdminAccessibility = {
  async loadAudits() {
    const el = document.getElementById("accessibility-audits-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/accessibility/audits");
      const rows = data.audits || [];
      if (!rows.length) { el.textContent = "لا توجد تدقيقات."; return; }
      el.innerHTML = rows.map((a) =>
        `<div class="border-b py-2"><a href="${a.page_url}" target="_blank" class="text-blue-600">${a.page_url}</a> — درجة: <strong>${a.score}</strong>/100</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const form = document.getElementById("audit-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        let issues;
        try { issues = JSON.parse(fd.get("issues") || "null"); } catch { issues = null; }
        await OrionAPI.post("/accessibility/audits", {
          page_url: fd.get("page_url"), score: parseInt(fd.get("score")), issues,
        });
        form.reset();
        OrionAdminAccessibility.loadAudits();
      });
    }
    OrionAdminAccessibility.loadAudits();
  },
};