/** Fraud admin — rules, reviews, chargebacks. */
const OrionAdminFraud = {
  async loadRules() {
    const el = document.getElementById("fraud-rules-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/fraud/rules");
      const rows = data.rules || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد قواعد.', 'No rules found.'); return; }
      SafeDOM.clear(el);
      for (const r of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2" }, [
          SafeDOM.elem("strong", {}, [r.name]),
          " — ", r.rule_type, " ", r.operator, " ", r.threshold_value, " → ", r.action
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
  },

  init() {
    const ruleForm = document.getElementById("fraud-rule-form");
    if (ruleForm) {
      ruleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(ruleForm);
        await OrionAPI.post("/fraud/rules", {
          name: fd.get("name"), rule_type: fd.get("rule_type"), operator: fd.get("operator"),
          threshold_value: fd.get("threshold_value"), action: fd.get("action"),
        });
        ruleForm.reset();
        OrionAdminFraud.loadRules();
      });
    }
    const reviewForm = document.getElementById("fraud-review-form");
    if (reviewForm) {
      reviewForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(reviewForm);
        await OrionAPI.post("/fraud/reviews", {
          order_id: parseInt(fd.get("order_id")), risk_score: parseInt(fd.get("risk_score") || "0"),
        });
        reviewForm.reset();
        alert(OrionI18n.t('تمت المراجعة', 'Reviewed'));
      });
    }
    OrionAdminFraud.loadRules();
  },
};