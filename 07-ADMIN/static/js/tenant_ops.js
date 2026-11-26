/** Tenant admin — RMA / B2B / OMS (wave 9 UI, MVP hardening). */
const OrionTenantOps = {
  async loadReturns() {
    const el = document.getElementById("returns-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/returns/");
      const rows = data.returns || [];
      if (!rows.length) {
        el.textContent = OrionI18n.t("لا توجد طلبات إرجاع.", "No return requests yet.");
        return;
      }
      SafeDOM.clear(el);
      for (const r of rows) {
        const row = SafeDOM.elem("div", { className: "border-b py-2 flex justify-between items-center gap-2" });
        row.appendChild(SafeDOM.elem("span", null, [`#${r.id} — ${r.status} — ${r.return_type || ""}`]));
        if (r.status === "requested") {
          row.appendChild(SafeDOM.elem("button", { "data-approve": r.id, className: "text-emerald-700 text-xs" }, [OrionI18n.t("موافقة", "Approve")]));
        }
        el.appendChild(row);
      }
      el.querySelectorAll("[data-approve]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await OrionAPI.put(`/returns/${btn.dataset.approve}/approve`);
          OrionTenantOps.loadReturns();
        });
      });
    } catch (err) {
      el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load");
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
        el.textContent = OrionI18n.t("لا توجد مجموعات.", "No groups.");
        return;
      }
      SafeDOM.clear(el);
      for (const g of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [`${g.name} (${g.code}) — ${OrionI18n.t("خصم", "Discount")} ${g.discount_percent}%`]));
      }
    } catch (err) {
      el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load");
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
        el.textContent = OrionI18n.t("لا توجد مستودعات.", "No warehouses.");
        return;
      }
      SafeDOM.clear(el);
      for (const w of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [`${w.name} (${w.code})${w.is_default ? ` — ${OrionI18n.t("افتراضي", "Default")}` : ""}`]));
      }
    } catch (err) {
      el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load");
    }
  },

  async loadTransfers() {
    const el = document.getElementById("oms-transfers-list");
    if (!el) return;
    try {
      const [data, wh] = await Promise.all([
        OrionAPI.get("/oms-ext/transfers"),
        OrionAPI.get("/oms/warehouses"),
      ]);
      const rows = data.transfers || [];
      const warehouses = wh.warehouses || [];
      for (const name of ["from_warehouse_id", "to_warehouse_id"]) {
        const select = document.querySelector(`#oms-transfer-form [name=${name}]`);
        if (!select) continue;
        const current = select.value;
        SafeDOM.clear(select);
        select.appendChild(SafeDOM.elem("option", { value: "" }, [name === "from_warehouse_id" ? OrionI18n.t("من مستودع...", "From warehouse...") : OrionI18n.t("إلى مستودع...", "To warehouse...")]));
        for (const w of warehouses) select.appendChild(SafeDOM.elem("option", { value: w.id }, [w.name]));
        select.value = current;
      }
      SafeDOM.clear(el);
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد تحويلات.", "No transfers."); return; }
      for (const t of rows) {
        const complete = t.status === "draft"
          ? SafeDOM.actionBtn(OrionI18n.t("إكمال", "Complete"), "orion-btn", async () => {
              try {
                await OrionAPI.post(`/oms-ext/transfers/${t.id}/complete`);
                OrionUI.toast(OrionI18n.t("تم إكمال التحويل", "Transfer completed"), "success");
                OrionTenantOps.loadTransfers();
              } catch (err) { OrionUI.toast(err.message, "error"); }
            })
          : null;
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex items-center justify-between" }, [
          SafeDOM.elem("span", {}, [`#${t.id} — ${t.status}`]), complete,
        ].filter(Boolean)));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  async loadOmsProducts() {
    const select = document.querySelector('#oms-transfer-item-form [name=product_id]');
    if (!select) return;
    try {
      const data = await OrionAPI.get("/oms/products");
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر منتجاً...", "Select a product...")]));
      for (const p of data.products || []) {
        select.appendChild(SafeDOM.elem("option", { value: p.id }, [`#${p.id} — ${p.name}`]));
      }
    } catch (err) {
      // Keep the manual input if the picker is unavailable.
    }
  },

  initOms() {
    OrionTenantOps.loadOmsProducts();
    const transferForm = document.getElementById("oms-transfer-form");
    if (transferForm) {
      transferForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(transferForm);
        try {
          await OrionAPI.post("/oms-ext/transfers", {
            from_warehouse_id: Number(fd.get("from_warehouse_id")),
            to_warehouse_id: Number(fd.get("to_warehouse_id")),
            notes: fd.get("notes") || undefined,
          });
          transferForm.reset();
          OrionUI.toast(OrionI18n.t("تم إنشاء التحويل", "Transfer created"), "success");
          OrionTenantOps.loadTransfers();
        } catch (err) { OrionUI.toast(err.message, "error"); }
      });
    }
    const itemForm = document.getElementById("oms-transfer-item-form");
    if (itemForm) {
      itemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(itemForm);
        try {
          await OrionAPI.post(`/oms-ext/transfers/${fd.get("transfer_id")}/items`, {
            product_id: Number(fd.get("product_id")),
            quantity: Number(fd.get("quantity")),
          });
          itemForm.reset();
          OrionUI.toast(OrionI18n.t("تمت إضافة الصنف", "Item added"), "success");
          OrionTenantOps.loadTransfers();
        } catch (err) { OrionUI.toast(err.message, "error"); }
      });
    }
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
    OrionTenantOps.loadTransfers();
  },

  async loadPlans() {
    const el = document.getElementById("plans-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/subscriptions/plans");
      const rows = data.plans || [];
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد خطط بعد.", "No plans yet."); return; }
      SafeDOM.clear(el);
      for (const p of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [`${p.name} (${p.code}) — ${p.price} ${p.currency} / ${p.billing_period_days} ${OrionI18n.t("يوم", "days")}${p.trial_period_days ? ` + ${p.trial_period_days} ${OrionI18n.t("يوم تجريبي", "trial days")}` : ""}`]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  async loadCustomerSubscriptions() {
    const el = document.getElementById("customer-subscriptions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/subscriptions/subscriptions");
      const rows = data.subscriptions || [];
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد اشتراكات حالية.", "No active subscriptions."); return; }
      SafeDOM.clear(el);
      for (const s of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [`${s.customer_email} — ${s.status} (${OrionI18n.t("تنتهي", "Expires")}: ${new Date(s.current_period_end).toLocaleDateString("ar")})`]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
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
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد مناطق ضريبية بعد.", "No tax jurisdictions yet."); return; }
      SafeDOM.clear(el);
      for (const j of rows) {
        const children = [
          SafeDOM.elem("strong", null, [j.name]),
          ` (${j.code}) — ${j.country}${j.region ? ` / ${j.region}` : ""}`
        ];
        if (j.rates && j.rates.length) {
          children.push(SafeDOM.elem("span", { className: "text-xs text-gray-500 mr-2" }, [`${j.rates.length} ${OrionI18n.t("معدّل", "rates")}`]));
        }
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, children));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  initTax() {
    const form = document.getElementById("tax-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/tax/jurisdictions", {
          name: fd.get("name"), code: fd.get("code"),
          country_code: fd.get("country"), region: fd.get("region") || undefined,
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
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد مواقع استلام.", "No pickup locations."); return; }
      SafeDOM.clear(el);
      for (const l of rows) {
        const a = l.address;
        const address = typeof a === "string"
          ? a
          : (a && (a.text || a.city || a.line1 || Object.values(a).join(OrionI18n.t("، ", ", ")))) || "";
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", null, [l.name]),
          ` — ${address}${l.phone ? ` (${l.phone})` : ""}`
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  initBopis() {
    const form = document.getElementById("bopis-location-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/bopis/locations", {
          code: fd.get("code") || String(fd.get("name") || "").trim().toLowerCase().replace(/\s+/g, "-"),
          name: fd.get("name"), address: { text: fd.get("address") },
          phone: fd.get("phone") || undefined,
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
      const data = await OrionAPI.get("/bundles");
      const rows = data.bundles || [];
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد حزم بعد.", "No bundles yet."); return; }
      SafeDOM.clear(el);
      const select = document.getElementById("bundle-item-bundle");
      if (select) {
        const current = select.value;
        SafeDOM.clear(select);
        select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر حزمة…", "Choose a bundle…")]));
        for (const b of rows) select.appendChild(SafeDOM.elem("option", { value: b.id }, [`#${b.id} — ${b.name}`]));
        select.value = current;
      }
      for (const b of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex items-center justify-between gap-2" }, [
          SafeDOM.elem("span", null, [
            SafeDOM.elem("strong", null, [b.name]),
            ` (${b.slug}) — ${b.bundle_price} ${b.currency || ""}`
          ]),
          SafeDOM.actionBtn(
            b.is_published ? OrionI18n.t("إلغاء النشر", "Unpublish") : OrionI18n.t("نشر", "Publish"),
            "orion-btn text-xs",
            async () => {
              await OrionAPI.put(`/bundles/${b.id}`, { is_published: !b.is_published });
              OrionTenantOps.loadBundles();
            }
          )
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  async loadBundleProducts() {
    const select = document.getElementById("bundle-item-product");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/oms/products");
      const current = select.value;
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر منتجاً…", "Choose a product…")]));
      for (const p of data.products || []) {
        select.appendChild(SafeDOM.elem("option", { value: p.id }, [`#${p.id} — ${p.name}`]));
      }
      select.value = current;
    } catch (err) { /* keep empty */ }
  },

  initBundles() {
    const form = document.getElementById("bundle-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/bundles", {
          name: fd.get("name"), slug: fd.get("slug"),
          bundle_price: String(fd.get("bundle_price") || "0"),
          description: fd.get("description") || undefined,
          image_url: fd.get("image_url") || undefined,
          max_per_order: fd.get("max_per_order") ? Number(fd.get("max_per_order")) : null,
          is_published: fd.get("is_published") === "on",
        });
        form.reset();
        OrionTenantOps.loadBundles();
      });
    }
    const itemForm = document.getElementById("bundle-item-form");
    if (itemForm) {
      itemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(itemForm);
        const msg = document.getElementById("bundle-item-msg");
        try {
          await OrionAPI.post(`/bundles/${fd.get("bundle_id")}/items`, {
            product_id: Number(fd.get("product_id")),
            quantity: Number(fd.get("quantity") || 1),
            discount_percent: String(fd.get("discount_percent") || "0"),
          });
          if (msg) msg.textContent = OrionI18n.t("تمت إضافة الصنف", "Item added");
          itemForm.reset();
        } catch (err) {
          if (msg) msg.textContent = err.message;
        }
      });
    }
    OrionTenantOps.loadBundleProducts();
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
          if (!txRows.length) { txEl.textContent = OrionI18n.t("لا توجد حركات.", "No transactions."); return; }
          SafeDOM.clear(txEl);
          for (const t of txRows) {
            txEl.appendChild(SafeDOM.elem("div", { className: "border-b py-1 text-sm" }, [`${t.type} — ${t.amount} — ${t.reason || ""} (${new Date(t.created_at).toLocaleDateString("ar")})`]));
          }
        } catch (err) {
          alert(err.message || OrionI18n.t("تعذّر تحميل الرصيد", "Failed to load balance"));
        }
      });
    }
  },

  async loadDraftOrders() {
    const el = document.getElementById("draft-orders-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/draft-orders");
      const rows = data.draft_orders || [];
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد مسودات.", "No drafts."); return; }
      SafeDOM.clear(el);
      for (const d of rows) {
        const row = SafeDOM.elem("div", { className: "border-b py-2 flex justify-between items-center" });
        row.appendChild(SafeDOM.elem("span", null, [
          SafeDOM.elem("strong", null, [`#${d.id}`]),
          ` — ${d.customer_email} — ${d.status}${d.notes ? ` (${d.notes})` : ""}`
        ]));
        if (d.status === "draft") {
          row.appendChild(SafeDOM.elem("button", { "data-convert": d.id, className: "text-emerald-700 text-xs" }, [OrionI18n.t("تحويل إلى طلب", "Convert to order")]));
        }
        el.appendChild(row);
      }
      el.querySelectorAll("[data-convert]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await OrionAPI.post(`/draft-orders/${btn.dataset.convert}/convert`);
          OrionTenantOps.loadDraftOrders();
        });
      });
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  initDraftOrders() {
    const form = document.getElementById("draft-order-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        await OrionAPI.post("/draft-orders", {
          customer_email: fd.get("customer_email"), notes: fd.get("notes") || undefined,
        });
        form.reset();
        OrionTenantOps.loadDraftOrders();
      });
    }
    OrionTenantOps.loadDraftOrders();
  },
};
