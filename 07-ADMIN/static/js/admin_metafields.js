/** Metafields admin — CRUD for definitions and values. */
const OrionAdminMetafields = {
  async loadDefinitions() {
    const el = document.getElementById("metafield-defs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/metafields/definitions");
      const rows = data.definitions || [];
      if (!rows.length) { el.textContent = "لا توجد تعريفات."; return; }
      el.innerHTML = rows.map((d) =>
        `<div class="border-b py-2"><strong>${d.key}</strong> (${d.owner_type}) — ${d.label} — ${d.field_type}${d.is_required ? " <span class='text-red-500'>*</span>" : ""}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const defForm = document.getElementById("metafield-def-form");
    if (defForm) {
      defForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(defForm);
        await OrionAPI.post("/metafields/definitions", {
          owner_type: fd.get("owner_type"), key: fd.get("key"), label: fd.get("label"),
          field_type: fd.get("field_type"), is_required: fd.get("is_required") === "on",
        });
        defForm.reset();
        OrionAdminMetafields.loadDefinitions();
      });
    }
    const valForm = document.getElementById("metafield-value-form");
    if (valForm) {
      valForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(valForm);
        await OrionAPI.post("/metafields/values", {
          definition_id: parseInt(fd.get("definition_id")), owner_id: parseInt(fd.get("owner_id")),
          value: fd.get("value") || undefined,
        });
        valForm.reset();
        alert("تم الحفظ");
      });
    }
    OrionAdminMetafields.loadDefinitions();
  },
};