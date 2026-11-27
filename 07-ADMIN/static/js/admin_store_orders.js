/** Review, confirm or cancel manual WhatsApp orders. */
const OrionStoreOrders = {
  async load() {
    const target = document.getElementById("manual-orders-list");
    if (!target) return;
    try {
      const data = await OrionAPI.get("/tenant/orders");
      SafeDOM.clear(target);
      const rows = data.orders || [];
      if (!rows.length) {
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3 orion-muted", colspan: "6" }, [OrionI18n.t("لا توجد طلبات بعد", "No orders yet")])
        ]));
        return;
      }
      rows.forEach((order) => {
        const items = (order.items || []).map(i => `${i.product_name} × ${i.quantity}`).join("، ");
        const pending = order.status === "awaiting";
        const actions = pending ? [
          SafeDOM.actionBtn(OrionI18n.t("تأكيد", "Confirm"), "orion-btn orion-btn-gold text-xs", () => this.update(order.public_id, "confirm")),
          SafeDOM.actionBtn(OrionI18n.t("إلغاء", "Cancel"), "orion-btn text-xs", () => this.update(order.public_id, "cancel")),
        ] : [SafeDOM.elem("span", { className: "orion-muted" }, [order.status])];
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-2" }, [order.order_number]),
          SafeDOM.elem("td", { className: "p-2" }, [order.customer_first_name || order.customer_email]),
          SafeDOM.elem("td", { className: "p-2" }, [items]),
          SafeDOM.elem("td", { className: "p-2" }, [`${order.total} ${order.currency || ""}`]),
          SafeDOM.elem("td", { className: "p-2" }, [order.status]),
          SafeDOM.elem("td", { className: "p-2" }, [SafeDOM.elem("div", { className: "flex gap-2" }, actions)]),
        ]));
      });
    } catch (err) {
      target.textContent = err.message;
    }
  },
  async update(publicId, action) {
    const msg = document.getElementById("manual-orders-msg");
    try {
      await OrionAPI.post(`/tenant/orders/${publicId}/${action}`, {});
      if (msg) msg.textContent = OrionI18n.t("تم تحديث الطلب", "Order updated");
      this.load();
    } catch (err) {
      if (msg) msg.textContent = err.message;
      OrionUI.toast(err.message, "error");
    }
  },
  init() { this.load(); },
};
