/** Dropship admin — POD, suppliers, orders. */
const OrionAdminDropship = {
  async loadPOD() {
    const el = document.getElementById("pod-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/dropship/pod");
      const rows = data.connections || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد اتصالات.', 'No connections found.'); return; }
      SafeDOM.clear(el);
      for (const c of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [c.provider]),
          " — ", c.api_url || OrionI18n.t('بدون رابط', 'No link')
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadSuppliers() {
    const el = document.getElementById("suppliers-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/dropship/suppliers");
      const rows = data.suppliers || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا يوجد موردون.', 'No suppliers found.'); return; }
      SafeDOM.clear(el);
      for (const s of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [s.name]),
          " — ", s.contact_email, " — ", s.fulfillment_time_days, OrionI18n.t(' يوم', ' days')
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadOrders() {
    const el = document.getElementById("dropship-orders-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/dropship/orders");
      const rows = data.orders || data.dropship_orders || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد طلبات.', 'No orders found.'); return; }
      SafeDOM.clear(el);
      for (const o of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          OrionI18n.t('مورد #', 'Supplier #'), o.supplier_id, OrionI18n.t(' — طلب #', ' — Order #'), o.order_id, " — ", o.cost
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  init() {
    const podForm = document.getElementById("pod-form");
    if (podForm) {
      podForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(podForm);
        await OrionAPI.post("/dropship/pod", {
          provider: fd.get("provider"), api_key: fd.get("api_key"), api_url: fd.get("api_url") || undefined,
        });
        podForm.reset();
        OrionAdminDropship.loadPOD();
      });
    }
    const supForm = document.getElementById("supplier-form");
    if (supForm) {
      supForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(supForm);
        await OrionAPI.post("/dropship/suppliers", {
          name: fd.get("name"), contact_email: fd.get("contact_email"),
          fulfillment_time_days: parseInt(fd.get("fulfillment_time_days") || "0"),
        });
        supForm.reset();
        OrionAdminDropship.loadSuppliers();
      });
    }
    const ordForm = document.getElementById("dropship-order-form");
    if (ordForm) {
      ordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(ordForm);
        await OrionAPI.post("/dropship/orders", {
          supplier_id: parseInt(fd.get("supplier_id")), order_id: parseInt(fd.get("order_id")), cost: fd.get("cost"),
        });
        ordForm.reset();
        OrionAdminDropship.loadOrders();
      });
    }
    OrionAdminDropship.loadPOD();
    OrionAdminDropship.loadSuppliers();
    OrionAdminDropship.loadOrders();
  },
};