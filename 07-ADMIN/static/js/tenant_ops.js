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

  async loadPlans() {
    const el = document.getElementById("plans-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/subscriptions/plans");
      const rows = data.plans || [];
      if (!rows.length) { el.textContent = "لا توجد خطط بعد."; return; }
      el.innerHTML = rows.map((p) =>
        `<div class="border-b py-2">${p.name} (${p.code}) — ${p.price} ${p.currency} / ${p.billing_period_days} يوم${p.trial_period_days ? ` + ${p.trial_period_days} يوم تجريبي` : ""}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadCustomerSubscriptions() {
    const el = document.getElementById("customer-subscriptions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/subscriptions/subscriptions");
      const rows = data.subscriptions || [];
      if (!rows.length) { el.textContent = "لا توجد اشتراكات حالية."; return; }
      el.innerHTML = rows.map((s) =>
        `<div class="border-b py-2">${s.customer_email} — ${s.status} (تنتهي: ${new Date(s.current_period_end).toLocaleDateString("ar")})</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  initSubscriptions() {
    const form = document.getElementById("plan-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/subscriptions/plans", {
          name: fd.get("name"), code: fd.get("code"), price: fd.get("price"),
          billing_period_days: parseInt(fd.get("billing_period_days")),
          trial_period_days: parseInt(fd.get("trial_period_days") || "0"),
          max_products: fd.get("max_products") ? parseInt(fd.get("max_products")) : null,
          max_orders_per_cycle: fd.get("max_orders_per_cycle") ? parseInt(fd.get("max_orders_per_cycle")) : null,
        });
        form.reset();
        OrionTenantOps.loadPlans();
      });
    }
    OrionTenantOps.loadPlans();
    OrionTenantOps.loadCustomerSubscriptions();
  },

  async loadTaxJurisdictions() {
    const el = document.getElementById("tax-jurisdictions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/tax/jurisdictions");
      const rows = data.jurisdictions || [];
      if (!rows.length) { el.textContent = "لا توجد مناطق ضريبية بعد."; return; }
      el.innerHTML = rows.map((j) =>
        `<div class="border-b py-2"><strong>${j.name}</strong> (${j.code}) — ${j.country}${j.region ? ` / ${j.region}` : ""}${j.rates && j.rates.length ? `<span class="text-xs text-gray-500 mr-2">${j.rates.length} معدّل</span>` : ""}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  initTax() {
    const form = document.getElementById("tax-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/tax/jurisdictions", {
          name: fd.get("name"), code: fd.get("code"),
          country: fd.get("country"), region: fd.get("region") || undefined,
        });
        form.reset();
        OrionTenantOps.loadTaxJurisdictions();
      });
    }
    OrionTenantOps.loadTaxJurisdictions();
  },

  async loadBopisLocations() {
    const el = document.getElementById("bopis-locations-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/bopis/locations");
      const rows = data.locations || [];
      if (!rows.length) { el.textContent = "لا توجد مواقع استلام."; return; }
      el.innerHTML = rows.map((l) =>
        `<div class="border-b py-2"><strong>${l.name}</strong> — ${l.address}${l.phone ? ` (${l.phone})` : ""}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  initBopis() {
    const form = document.getElementById("bopis-location-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/bopis/locations", {
          name: fd.get("name"), address: fd.get("address"), phone: fd.get("phone") || undefined,
        });
        form.reset();
        OrionTenantOps.loadBopisLocations();
      });
    }
    OrionTenantOps.loadBopisLocations();
  },

  async loadBundles() {
    const el = document.getElementById("bundles-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/bundles/");
      const rows = data.bundles || [];
      if (!rows.length) { el.textContent = "لا توجد حزم بعد."; return; }
      el.innerHTML = rows.map((b) =>
        `<div class="border-b py-2"><strong>${b.name}</strong> (${b.code}) — خصم ${b.discount_percent}%</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  initBundles() {
    const form = document.getElementById("bundle-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/bundles/", {
          name: fd.get("name"), code: fd.get("code"),
          discount_percent: String(fd.get("discount_percent") || "0"),
        });
        form.reset();
        OrionTenantOps.loadBundles();
      });
    }
    OrionTenantOps.loadBundles();
  },

  initStoreCredit() {
    const lookupBtn = document.getElementById("lookup-credit");
    const emailInput = document.getElementById("credit-customer-email");
    if (lookupBtn && emailInput) {
      lookupBtn.addEventListener("click", async () => {
        const email = emailInput.value.trim();
        if (!email) return;
        try {
          const data = await OrionAPI.get(`/store-credit/balance?customer_email=${encodeURIComponent(email)}`);
          const balanceEl = document.getElementById("credit-balance");
          const amountEl = document.getElementById("credit-amount");
          balanceEl.classList.remove("hidden");
          amountEl.textContent = data.balance || "0.00";

          const addForm = document.getElementById("credit-add-form");
          addForm.classList.remove("hidden");
          addForm.onsubmit = async (e) => {
            e.preventDefault();
            const fd = new FormData(addForm);
            await OrionAPI.post("/store-credit/add", {
              customer_email: email, amount: String(fd.get("amount")), reason: fd.get("reason") || undefined,
            });
            addForm.reset();
            location.reload();
          };

          const txEl = document.getElementById("credit-transactions");
          const txData = await OrionAPI.get(`/store-credit/transactions?customer_email=${encodeURIComponent(email)}`);
          const txRows = txData.transactions || [];
          if (!txRows.length) { txEl.textContent = "لا توجد حركات."; return; }
          txEl.innerHTML = txRows.map((t) =>
            `<div class="border-b py-1 text-sm">${t.type} — ${t.amount} — ${t.reason || ""} (${new Date(t.created_at).toLocaleDateString("ar")})</div>`
          ).join("");
        } catch (err) {
          alert(err.message || "تعذّر تحميل الرصيد");
        }
      });
    }
  },

  async loadDraftOrders() {
    const el = document.getElementById("draft-orders-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/draft-orders/");
      const rows = data.draft_orders || [];
      if (!rows.length) { el.textContent = "لا توجد مسودات."; return; }
      el.innerHTML = rows.map((d) =>
        `<div class="border-b py-2 flex justify-between items-center">
          <span><strong>#${d.id}</strong> — ${d.customer_email} — ${d.status}${d.notes ? ` (${d.notes})` : ""}</span>
          ${d.status === "draft" ? `<button data-convert="${d.id}" class="text-emerald-700 text-xs">تحويل إلى طلب</button>` : ""}
        </div>`
      ).join("");
      el.querySelectorAll("[data-convert]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await OrionAPI.post(`/draft-orders/${btn.dataset.convert}/convert`);
          OrionTenantOps.loadDraftOrders();
        });
      });
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  initDraftOrders() {
    const form = document.getElementById("draft-order-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/draft-orders/", {
          customer_email: fd.get("customer_email"), notes: fd.get("notes") || undefined,
        });
        form.reset();
        OrionTenantOps.loadDraftOrders();
      });
    }
    OrionTenantOps.loadDraftOrders();
  },
};
