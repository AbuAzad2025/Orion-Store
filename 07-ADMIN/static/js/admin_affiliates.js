/** Affiliates admin — programs, affiliates, commissions. */
const OrionAdminAffiliates = {
  async loadPrograms() {
    const el = document.getElementById("affiliate-programs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/affiliates/programs");
      const rows = data.programs || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد برامج.', 'No programs.'); return; }
      SafeDOM.clear(el);
      for (const p of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [p.name]),
          " (", p.code, ") — ", p.commission_type, " ", p.commission_value
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadAffiliates() {
    const el = document.getElementById("affiliates-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/affiliates/affiliates");
      const rows = data.affiliates || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا يوجد مسوقون.', 'No affiliates.'); return; }
      SafeDOM.clear(el);
      for (const a of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          a.email, " — ", a.referral_code, " — ", a.total_earned || 0
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  async loadCommissions() {
    const el = document.getElementById("commissions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/affiliates/commissions");
      const rows = data.commissions || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد عمولات.', 'No commissions.'); return; }
      SafeDOM.clear(el);
      for (const c of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          OrionI18n.t('مسوق', 'Affiliate') + " #", c.affiliate_id, " — " + OrionI18n.t('طلب', 'Order') + " #", c.order_id, " — ", c.amount
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  init() {
    const progForm = document.getElementById("affiliate-program-form");
    if (progForm) {
      progForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(progForm);
        await OrionAPI.post("/affiliates/programs", {
          name: fd.get("name"), code: fd.get("code"), commission_type: fd.get("commission_type"),
          commission_value: fd.get("commission_value"), cookie_days: parseInt(fd.get("cookie_days") || "30"),
        });
        progForm.reset();
        OrionAdminAffiliates.loadPrograms();
      });
    }
    const regForm = document.getElementById("affiliate-register-form");
    if (regForm) {
      regForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(regForm);
        await OrionAPI.post("/affiliates/register", {
          program_id: parseInt(fd.get("program_id")), email: fd.get("email"),
        });
        regForm.reset();
        OrionAdminAffiliates.loadAffiliates();
      });
    }
    const commForm = document.getElementById("affiliate-commission-form");
    if (commForm) {
      commForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(commForm);
        await OrionAPI.post("/affiliates/commissions", {
          affiliate_id: parseInt(fd.get("affiliate_id")), order_id: parseInt(fd.get("order_id")),
          amount: fd.get("amount"),
        });
        commForm.reset();
        OrionAdminAffiliates.loadCommissions();
      });
    }
    OrionAdminAffiliates.loadPrograms();
    OrionAdminAffiliates.loadAffiliates();
    OrionAdminAffiliates.loadCommissions();
  },
};