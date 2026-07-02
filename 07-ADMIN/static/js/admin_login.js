/** Admin login — sets tenant context for API calls after server-side login. */
document.addEventListener("DOMContentLoaded", () => {
  localStorage.removeItem("orion_access_token");
  const tenantSlug = document.getElementById("tenant-slug")?.value?.trim();
  if (tenantSlug) document.body.dataset.tenantId = tenantSlug;
});
