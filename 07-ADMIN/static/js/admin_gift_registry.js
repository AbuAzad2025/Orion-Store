/** Gift Registry admin. */
const OrionAdminGiftRegistry = {
  async loadRegistries() {
    const el = document.getElementById("gift-registries-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/gift-registries/");
      const rows = data.registries || [];
      if (!rows.length) { el.textContent = "لا توجد قوائم."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2"><strong>${r.registry_name}</strong> — ${r.customer_email} — ${r.event_type || ""} — ${r.is_public ? "عامة" : "خاصة"}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const form = document.getElementById("gift-registry-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/gift-registries/", {
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