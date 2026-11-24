/** Vouchers admin — list and create discount coupons. */
const OrionAdminVouchers = {
  async loadVouchers() {
    const el = document.getElementById("vouchers-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/vouchers/");
      const rows = data.vouchers || [];
      SafeDOM.clear(el);
      if (!rows.length) {
        el.appendChild(SafeDOM.elem("p", { className: "orion-muted" }, [OrionI18n.t('لا توجد قسائم.', 'No vouchers.')]));
        return;
      }
      for (const v of rows) {
        const remove = SafeDOM.actionBtn(OrionI18n.t('حذف', 'Delete'), "orion-btn", async () => {
          if (!OrionUI.confirmDanger(`${OrionI18n.t('حذف القسيمة', 'Delete voucher')} ${v.code}?`)) return;
          try {
            await OrionAPI.delete(`/vouchers/${encodeURIComponent(v.code)}`);
            OrionUI.toast(OrionI18n.t('تم حذف القسيمة', 'Voucher deleted'), "success");
            OrionAdminVouchers.loadVouchers();
          } catch (err) { OrionUI.toast(err.message, "error"); }
        });
        el.appendChild(SafeDOM.elem("div", { className: "border-b border-slate-800 py-2 flex items-center justify-between" }, [
          SafeDOM.elem("span", {}, [
            SafeDOM.elem("strong", {}, [v.code]), " — ", v.value,
            " ", v.type === "percentage" ? "%" : "₪",
            " — " + OrionI18n.t('مستخدم', 'Used') + ": ", v.usage_count ?? 0, "/", v.usage_limit ?? "∞"
          ]),
          remove
        ]));
      }
    } catch (err) { OrionUI.toast(err.message, "error"); }
  },

  init() {
    const form = document.getElementById("voucher-form");
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("voucher-msg");
      const start = document.getElementById("v-start").value;
      const end = document.getElementById("v-end").value;
      try {
        await OrionUI.withLoading(form, () => OrionAPI.post("/vouchers/", {
          code: document.getElementById("v-code").value.trim(),
          name: document.getElementById("v-name").value.trim(),
          type: document.getElementById("v-type").value,
          value: document.getElementById("v-value").value,
          usage_limit: document.getElementById("v-limit").value || null,
          start_date: start ? `${start}T00:00:00Z` : null,
          end_date: end ? `${end}T23:59:59Z` : null,
          is_free_shipping: document.getElementById("v-free-shipping").checked,
        }));
        form.reset();
        msg.textContent = OrionI18n.t('تم حفظ القسيمة', 'Voucher saved');
        OrionUI.toast(msg.textContent, "success");
        OrionAdminVouchers.loadVouchers();
      } catch (err) {
        msg.textContent = err.message;
        OrionUI.toast(err.message, "error");
      }
    });
    document.getElementById("btn-refresh")?.addEventListener("click", () => OrionAdminVouchers.loadVouchers());
    OrionAdminVouchers.loadVouchers();
  },
};
