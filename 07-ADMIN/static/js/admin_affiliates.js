/** Affiliates admin — programs, affiliates, commissions. */
const OrionAdminAffiliates = {
  async loadPrograms() {
    const el = document.getElementById("affiliate-programs-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/affiliates/programs");
      const rows = data.programs || [];
      if (!rows.length) { el.textContent = "لا توجد برامج."; return; }
      SafeDOM.clear(el);
      for (const p of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [p.name]),
          " (", p.code, ") — ", p.commission_type, " ", p.commission_value
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadAffiliates() {
    const el = document.getElementById("affiliates-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/affiliates/affiliates");
      const rows = data.affiliates || [];
      if (!rows.length) { el.textContent = "لا يوجد مسوقون."; return; }
      SafeDOM.clear(el);
      for (const a of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          a.email, " — ", a.referral_code, " — ", a.total_earned || 0
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadCommissions() {
    const el = document.getElementById("commissions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/affiliates/commissions");
      const rows = data.commissions || [];
      if (!rows.length) { el.textContent = "لا توجد عمولات."; return; }
      SafeDOM.clear(el);
      for (const c of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          "مسوق #", c.affiliate_id, " — طلب #", c.order_id, " — ", c.amount
        ]));
      }
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
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