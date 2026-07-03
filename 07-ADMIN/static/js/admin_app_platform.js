/** App Platform admin — OAuth apps, installations, sandboxes. */
const OrionAdminAppPlatform = {
  async loadApps() {
    const el = document.getElementById("apps-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/app-platform/apps");
      const rows = data.apps || [];
      if (!rows.length) { el.textContent = "لا توجد تطبيقات."; return; }
      SafeDOM.clear(el);
      for (const a of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [a.name]),
          " — ", a.client_id
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadSandboxes() {
    const el = document.getElementById("sandboxes-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/app-platform/sandboxes");
      const rows = data.sandboxes || [];
      if (!rows.length) { el.textContent = "لا توجد sandbox."; return; }
      SafeDOM.clear(el);
      for (const s of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          s.slug, " — ", s.name
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const appForm = document.getElementById("app-form");
    if (appForm) {
      appForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(appForm);
        await OrionAPI.post("/app-platform/apps", {
          name: fd.get("name"), redirect_uris: (fd.get("redirect_uris") || "").split(",").map((s) => s.trim()).filter(Boolean),
          scopes: fd.get("scopes") || undefined,
        });
        appForm.reset();
        OrionAdminAppPlatform.loadApps();
      });
    }
    const sbForm = document.getElementById("sandbox-form");
    if (sbForm) {
      sbForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(sbForm);
        await OrionAPI.post("/app-platform/sandboxes", {
          slug: fd.get("slug"), name: fd.get("name"), expires_at: fd.get("expires_at") || undefined,
        });
        sbForm.reset();
        OrionAdminAppPlatform.loadSandboxes();
      });
    }
    OrionAdminAppPlatform.loadApps();
    OrionAdminAppPlatform.loadSandboxes();
  },
};