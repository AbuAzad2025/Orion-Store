/** Admin login — stores JWT and redirects (wave 5 gap closure). */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  const err = document.getElementById("login-error");
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    err.textContent = "";
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const tenantSlug = document.getElementById("tenant-slug").value.trim();
    const body = { email, password };
    if (tenantSlug) body.tenant_id = tenantSlug;
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Login failed");
      OrionAPI.setToken(data.access_token);
      if (tenantSlug) document.body.dataset.tenantId = tenantSlug;
      if (data.user && data.user.is_superuser) {
        window.location.href = "/admin/platform/dashboard";
      } else {
        window.location.href = "/admin/store/dashboard";
      }
    } catch (e) {
      err.textContent = e.message;
    }
  });
});
