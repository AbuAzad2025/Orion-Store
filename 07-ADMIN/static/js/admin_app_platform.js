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

  // One-time reveal: the button is shown once after registration and removes
  // itself as soon as it is used — the raw secret is never persisted or shown
  // again by any subsequent API call.
  offerClientSecret(secret) {
    const form = document.getElementById("app-form");
    let panel = document.getElementById("oauth-secret-panel");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "oauth-secret-panel";
      panel.className = "border border-amber-300 bg-amber-50 p-3 my-3 rounded";
      if (form && form.parentNode) form.parentNode.insertBefore(panel, form.nextSibling);
      else document.body.appendChild(panel);
    }
    SafeDOM.clear(panel);
    panel.appendChild(SafeDOM.elem("span", {}, ["client_secret (يُعرض مرة واحدة فقط): "]));
    const btn = SafeDOM.elem("button", {
      type: "button",
      className: "orion-btn ml-2",
    }, ["إنشاء client_secret"]);
    btn.addEventListener("click", async () => {
      try {
        if (navigator.clipboard) await navigator.clipboard.writeText(secret);
      } catch (_) { /* clipboard may be blocked — secret is still displayed */ }
      SafeDOM.clear(panel);
      panel.appendChild(SafeDOM.elem("code", {}, [secret]));
      btn.remove();
    });
    panel.appendChild(btn);
  },

  init() {
    const appForm = document.getElementById("app-form");
    if (appForm) {
      appForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(appForm);
        const result = await OrionAPI.post("/app-platform/apps", {
          name: fd.get("name"), redirect_uris: (fd.get("redirect_uris") || "").split(",").map((s) => s.trim()).filter(Boolean),
          scopes: fd.get("scopes") || undefined,
        });
        appForm.reset();
        OrionAdminAppPlatform.loadApps();
        // The API returns the raw client_secret exactly once, at registration.
        const secret = result && (result.client_secret || (result.app && result.app.client_secret));
        if (secret) OrionAdminAppPlatform.offerClientSecret(secret);
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