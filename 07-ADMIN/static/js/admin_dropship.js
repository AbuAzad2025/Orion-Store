/** Dropship admin — POD, suppliers, orders. */
const OrionAdminDropship = {
  async loadPOD() {
    const el = document.getElementById("pod-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/dropship/pod");
      const rows = data.connections || [];
      if (!rows.length) { el.textContent = "لا توجد اتصالات."; return; }
      SafeDOM.clear(el);
      for (const c of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [c.provider]),
          " — ", c.api_url || "بدون رابط"
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadSuppliers() {
    const el = document.getElementById("suppliers-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/dropship/suppliers");
      const rows = data.suppliers || [];
      if (!rows.length) { el.textContent = "لا يوجد موردون."; return; }
      SafeDOM.clear(el);
      for (const s of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [s.name]),
          " — ", s.contact_email, " — ", s.fulfillment_time_days, " يوم"
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadOrders() {
    const el = document.getElementById("dropship-orders-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/dropship/orders");
      const rows = data.dropship_orders || [];
      if (!rows.length) { el.textContent = "لا توجد طلبات."; return; }
      SafeDOM.clear(el);
      for (const o of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          "مورد #", o.supplier_id, " — طلب #", o.order_id, " — ", o.cost
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
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