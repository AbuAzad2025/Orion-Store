/** Workflows admin — definitions and runs. */
const OrionAdminWorkflows = {
  async loadDefinitions() {
    const el = document.getElementById("workflow-defs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/workflow/definitions");
      const rows = data.definitions || [];
      if (!rows.length) { el.textContent = "لا توجد تعريفات."; return; }
      el.innerHTML = rows.map((d) =>
        `<div class="border-b py-2"><strong>${d.name}</strong> — ${d.trigger_event}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadRuns() {
    const el = document.getElementById("workflow-runs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/workflow/runs");
      const rows = data.runs || [];
      if (!rows.length) { el.textContent = "لا توجد تشغيلات."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2">#${r.id} — ${r.status}${r.error_message ? ` <span class="text-red-500">${r.error_message}</span>` : ""}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const form = document.getElementById("workflow-def-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        let actions, conditions;
        try { actions = JSON.parse(fd.get("actions") || "[]"); } catch { actions = []; }
        try { conditions = JSON.parse(fd.get("conditions") || "null"); } catch { conditions = null; }
        await OrionAPI.post("/workflow/definitions", {
          name: fd.get("name"), trigger_event: fd.get("trigger_event"), actions, conditions,
        });
        form.reset();
        OrionAdminWorkflows.loadDefinitions();
      });
    }
    OrionAdminWorkflows.loadDefinitions();
    OrionAdminWorkflows.loadRuns();
  },
};