/** Tenant warehouse inventory — list and update stock quantities. */
const OrionAdminInventory = {
  async load() {
    const target = document.getElementById("inventory-list");
    if (!target) return;
    const select = document.getElementById("inventory-warehouse");
    const warehouseId = select?.value || "";
    try {
      const data = await OrionAPI.get(`/oms/inventory${warehouseId ? "?warehouse_id=" + warehouseId : ""}`);
      SafeDOM.clear(target);
      const rows = data.inventory || [];
      if (!rows.length) {
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3 orion-muted", colspan: "5" }, [OrionI18n.t("لا يوجد مخزون مسجل", "No stock recorded")])
        ]));
        return;
      }
      const warehouses = [...(select?.options || [])].map((o) => [o.value, o.text]);
      const wnames = Object.fromEntries(warehouses);
      rows.forEach((row) => {
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-2" }, [row.product_name]),
          SafeDOM.elem("td", { className: "p-2" }, [wnames[String(row.warehouse_id)] || row.warehouse_id]),
          SafeDOM.elem("td", { className: "p-2" }, [row.quantity]),
          SafeDOM.elem("td", { className: "p-2" }, [row.reserved_quantity]),
          SafeDOM.elem("td", { className: "p-2" }, [row.available]),
        ]));
      });
    } catch (err) {
      target.textContent = err.message;
    }
  },

  async loadWarehouses() {
    const select = document.getElementById("inventory-warehouse");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/oms/warehouses");
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر مستودعاً…", "Choose a warehouse…")]));
      (data.warehouses || []).forEach((w) =>
        select.appendChild(SafeDOM.elem("option", { value: w.id }, [w.name]))
      );
    } catch (err) { /* keep the placeholder */ }
    this.load();
  },

  async loadProducts() {
    const select = document.getElementById("inventory-product");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/oms/products");
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر منتجاً…", "Choose a product…")]));
      (data.products || []).forEach((p) => select.appendChild(SafeDOM.elem("option", { value: p.id }, [p.name])));
    } catch (err) { /* keep empty */ }
  },

  init() {
    const form = document.getElementById("inventory-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const msg = document.getElementById("inventory-msg");
        try {
          await OrionAPI.put("/oms/inventory", {
            warehouse_id: Number(fd.get("warehouse_id")),
            product_id: Number(fd.get("product_id")),
            quantity: Number(fd.get("quantity") || 0),
          });
          if (msg) msg.textContent = OrionI18n.t("تم تحديث المخزون", "Stock updated");
          this.load();
        } catch (err) {
          if (msg) msg.textContent = err.message;
        }
      });
    }
    document.getElementById("inventory-warehouse")?.addEventListener("change", () => this.load());
    this.loadProducts();
    this.loadWarehouses();
  },
};
