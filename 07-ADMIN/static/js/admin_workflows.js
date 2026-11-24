/** Workflows admin — definitions and runs. */
const OrionAdminWorkflows = {
  async loadDefinitions() {
    const el = document.getElementById("workflow-defs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/workflow/definitions");
      const rows = data.definitions || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد تعريفات.', 'No definitions found.'); return; }
      SafeDOM.clear(el);
      for (const d of rows) {
        const runBtn = SafeDOM.actionBtn(OrionI18n.t('تشغيل', 'Run'), "orion-btn", async () => {
          try {
            await OrionAPI.post(`/workflow/definitions/${d.id}/run`);
            OrionUI.toast(OrionI18n.t('تم تشغيل سير العمل', 'Workflow started'), "success");
            OrionAdminWorkflows.loadRuns();
          } catch (err) { OrionUI.toast(err.message, "error"); }
        });
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex items-center justify-between" }, [
          SafeDOM.elem("span", {}, [SafeDOM.elem("strong", {}, [d.name]), " — ", d.trigger_event]),
          runBtn
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadRuns() {
    const el = document.getElementById("workflow-runs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/workflow/runs");
      const rows = data.runs || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد تشغيلات.', 'No runs found.'); return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        const children = ["#", r.id, " — ", r.status];
        if (r.error_message) {
          children.push(" ", SafeDOM.elem("span", { className: "text-red-500" }, [r.error_message]));
        }
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, children));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
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