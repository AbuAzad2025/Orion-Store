/** Workflows admin — definitions and runs. */
const OrionAdminWorkflows = {
  async loadDefinitions() {
    const el = document.getElementById("workflow-defs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/workflow/definitions");
      const rows = data.definitions || [];
      if (!rows.length) { el.textContent = "لا توجد تعريفات."; return; }
      SafeDOM.clear(el);
      for (const d of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [d.name]),
          " — ", d.trigger_event
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadRuns() {
    const el = document.getElementById("workflow-runs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/workflow/runs");
      const rows = data.runs || [];
      if (!rows.length) { el.textContent = "لا توجد تشغيلات."; return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        const children = ["#", r.id, " — ", r.status];
        if (r.error_message) {
          children.push(" ", SafeDOM.elem("span", { className: "text-red-500" }, [r.error_message]));
        }
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, children));
      }
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