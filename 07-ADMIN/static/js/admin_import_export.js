/** Import/Export jobs admin. */
const OrionAdminImportExport = {
  async loadJobs() {
    const el = document.getElementById("import-export-jobs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/import-export/jobs");
      const rows = data.jobs || [];
      if (!rows.length) { el.textContent = "لا توجد مهام."; return; }
      SafeDOM.clear(el);
      for (const j of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [j.job_type]),
          " — ", j.entity_type, " — ", j.status || "pending", " (", j.processed_count || 0, "/", j.total_count || 0, ")"
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const form = document.getElementById("import-export-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const payload = { job_type: fd.get("job_type"), entity_type: fd.get("entity_type") };
        const fileUrl = fd.get("file_url");
        if (fileUrl) payload.file_url = fileUrl;
        await OrionAPI.post("/import-export/jobs", payload);
        form.reset();
        OrionAdminImportExport.loadJobs();
      });
    }
    OrionAdminImportExport.loadJobs();
  },
};