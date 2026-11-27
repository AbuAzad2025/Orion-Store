/** Admin login — sets tenant context for API calls after server-side login. */
document.addEventListener("DOMContentLoaded", () => {
  const tenantSlug = document.querySelector('input[name="tenant_slug"]')?.value?.trim();
  if (tenantSlug) document.body.dataset.tenantId = tenantSlug;
});
