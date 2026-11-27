/** Tenant sales & profit report. */
const OrionAdminReports = {
  async load(from, to) {
    const msg = document.getElementById("sales-msg");
    const summary = document.getElementById("sales-summary");
    const top = document.getElementById("sales-top");
    if (!summary || !top) return;
    try {
      const query = new URLSearchParams();
      if (from) query.set("from", from);
      if (to) query.set("to", to);
      const data = await OrionAPI.get(`/tenant/reports/sales${query.size ? "?" + query : ""}`);
      const r = data.report;
      const cards = [
        [OrionI18n.t("الطلبات المدفوعة", "Paid orders"), r.orders_count],
        [OrionI18n.t("المبيعات", "Revenue"), r.revenue],
        [OrionI18n.t("تكلفة البضائع", "Cost of goods"), r.cogs],
        [OrionI18n.t("الربح الإجمالي", "Gross profit"), `${r.gross_profit} (${r.margin_percent}%)`],
      ];
      SafeDOM.clear(summary);
      cards.forEach(([label, value]) => {
        summary.appendChild(SafeDOM.elem("div", { className: "orion-card p-4" }, [
          SafeDOM.elem("p", { className: "orion-stat-label" }, [label]),
          SafeDOM.elem("strong", { className: "orion-stat-value" }, [String(value)]),
        ]));
      });
      SafeDOM.clear(top);
      (r.top_products || []).forEach((p) => {
        top.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-2" }, [p.name]),
          SafeDOM.elem("td", { className: "p-2" }, [p.quantity]),
          SafeDOM.elem("td", { className: "p-2" }, [p.revenue]),
        ]));
      });
      if (!(r.top_products || []).length) {
        top.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3 orion-muted", colspan: "3" }, [OrionI18n.t("لا توجد بيانات", "No data")])
        ]));
      }
      if (msg) msg.textContent = OrionI18n.t("تم تحديث التقرير", "Report updated");
    } catch (err) {
      if (msg) msg.textContent = err.message;
      OrionUI.toast(err.message, "error");
    }
  },

  init() {
    const form = document.getElementById("sales-report-form");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        this.load(fd.get("from"), fd.get("to"));
      });
    }
    document.getElementById("sales-clear")?.addEventListener("click", () => {
      form?.reset();
      this.load("", "");
    });
    this.load("", "");
  },
};
