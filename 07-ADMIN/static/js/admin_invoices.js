/** Tenant invoice list with PDF download links. */
const OrionAdminInvoices = {
  async load() {
    const target = document.getElementById("invoices-list");
    const msg = document.getElementById("invoices-msg");
    if (!target) return;
    try {
      const data = await OrionAPI.get("/tenant/invoices");
      SafeDOM.clear(target);
      const rows = data.invoices || [];
      if (!rows.length) {
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3 orion-muted", colspan: "6" }, [OrionI18n.t("لا توجد فواتير بعد", "No invoices yet")])
        ]));
        return;
      }
      rows.forEach((invoice) => {
        const pdf = invoice.public_id
          ? `/api/v1/tenant/invoices/${invoice.public_id}/pdf`
          : "#";
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-2" }, [invoice.invoice_number]),
          SafeDOM.elem("td", { className: "p-2" }, [invoice.order_number]),
          SafeDOM.elem("td", { className: "p-2" }, [`${invoice.tax_amount} ${invoice.currency}`]),
          SafeDOM.elem("td", { className: "p-2" }, [`${invoice.total_amount} ${invoice.currency}`]),
          SafeDOM.elem("td", { className: "p-2" }, [(invoice.issued_at || "").slice(0, 10)]),
          SafeDOM.elem("td", { className: "p-2" }, [
            SafeDOM.elem("a", { className: "orion-btn text-xs", href: pdf, target: "_blank", rel: "noopener" }, [OrionI18n.t("تحميل", "Download")])
          ]),
        ]));
      });
      if (msg) msg.textContent = OrionI18n.t("تم تحميل الفواتير", "Invoices loaded");
    } catch (err) {
      if (msg) msg.textContent = err.message;
      OrionUI.toast(err.message, "error");
    }
  },
  init() { this.load(); },
};
