/** Schema Markup admin. */
const OrionAdminSchema = {
  async loadMarkup() {
    const el = document.getElementById("schema-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/schema-markup/");
      const rows = data.markups || [];
      if (!rows.length) { el.textContent = "لا توجد إعدادات."; return; }
      SafeDOM.clear(el);
      for (const m of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          "منتج #", m.product_id, " — ", m.schema_type
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const form = document.getElementById("schema-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        let jsonLd;
        try { jsonLd = JSON.parse(fd.get("json_ld") || "{}"); } catch { jsonLd = {}; }
        await OrionAPI.post("/schema-markup/", {
          product_id: parseInt(fd.get("product_id")), schema_type: fd.get("schema_type"), json_ld: jsonLd,
        });
        form.reset();
        OrionAdminSchema.loadMarkup();
      });
    }
    OrionAdminSchema.loadMarkup();
  },
};