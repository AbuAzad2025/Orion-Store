/** Tenant admin — RMA / B2B / OMS (wave 9 UI, MVP hardening). */
const OrionTenantOps = {
  async loadReturns() {
    const el = document.getElementById("returns-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/returns/");
      const rows = data.returns || [];
      if (!rows.length) {
        el.textContent = "لا توجد طلبات إرجاع.";
        return;
      }
      el.innerHTML = rows
        .map(
          (r) => `<div class="border-b py-2 flex justify-between items-center gap-2">
            <span>#${r.id} — ${r.status} — ${r.return_type || ""}</span>
            ${
              r.status === "pending"
                ? `<button data-approve="${r.id}" class="text-emerald-700 text-xs">موافقة</button>`
                : ""
            }
          </div>`
        )
        .join("");
      el.querySelectorAll("[data-approve]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await OrionAPI.put(`/returns/${btn.dataset.approve}/approve`);
          OrionTenantOps.loadReturns();
        });
      });
    } catch (err) {
      el.textContent = err.message || "تعذّر التحميل";
    }
  },

  initReturns() {
    OrionTenantOps.loadReturns();
  },

  async loadB2bGroups() {
    const el = document.getElementById("b2b-groups-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/b2b/customer-groups");
      const rows = data.groups || [];
      if (!rows.length) {
        el.textContent = "لا توجد مجموعات.";
        return;
      }
      el.innerHTML = rows
        .map(
          (g) =>
            `<div class="border-b py-2">${g.name} (${g.code}) — خصم ${g.discount_percent}%</div>`
        )
        .join("");
    } catch (err) {
      el.textContent = err.message || "تعذّر التحميل";
    }
  },

  initB2b() {
    const form = document.getElementById("b2b-group-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/b2b/customer-groups", {
          name: fd.get("name"),
          code: fd.get("code"),
          discount_percent: String(fd.get("discount_percent") || "0"),
        });
        form.reset();
        OrionTenantOps.loadB2bGroups();
      });
    }
    OrionTenantOps.loadB2bGroups();
  },

  async loadWarehouses() {
    const el = document.getElementById("oms-warehouses-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/oms/warehouses");
      const rows = data.warehouses || [];
      if (!rows.length) {
        el.textContent = "لا توجد مستودعات.";
        return;
      }
      el.innerHTML = rows
        .map(
          (w) =>
            `<div class="border-b py-2">${w.name} (${w.code})${
              w.is_default ? " — افتراضي" : ""
            }</div>`
        )
        .join("");
    } catch (err) {
      el.textContent = err.message || "تعذّر التحميل";
    }
  },

  initOms() {
    const form = document.getElementById("oms-warehouse-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/oms/warehouses", {
          name: fd.get("name"),
          code: fd.get("code"),
          is_default: fd.get("is_default") === "on",
        });
        form.reset();
        OrionTenantOps.loadWarehouses();
      });
    }
    OrionTenantOps.loadWarehouses();
  },
};
