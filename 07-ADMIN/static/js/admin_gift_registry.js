/** Gift Registry admin. */
const OrionAdminGiftRegistry = {
  async loadRegistries() {
    const el = document.getElementById("gift-registries-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/gift-registries");
      const rows = data.registries || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد قوائم.', 'No registries found.'); return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [r.registry_name]),
          " — ", r.customer_email, " — ", r.event_type || "", " — ", r.is_public ? OrionI18n.t('عامة', 'Public') : OrionI18n.t('خاصة', 'Private')
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  init() {
    const form = document.getElementById("gift-registry-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/gift-registries", {
          customer_email: fd.get("customer_email"), registry_name: fd.get("registry_name"),
          event_type: fd.get("event_type") || undefined, event_date: fd.get("event_date") || undefined,
          is_public: fd.get("is_public") === "on",
        });
        form.reset();
        OrionAdminGiftRegistry.loadRegistries();
      });
    }
    OrionAdminGiftRegistry.loadRegistries();
  },
};