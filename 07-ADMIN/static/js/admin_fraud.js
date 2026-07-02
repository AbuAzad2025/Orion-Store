/** Fraud admin — rules, reviews, chargebacks. */
const OrionAdminFraud = {
  async loadRules() {
    const el = document.getElementById("fraud-rules-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/fraud/rules");
      const rows = data.rules || [];
      if (!rows.length) { el.textContent = "لا توجد قواعد."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2"><strong>${r.name}</strong> — ${r.rule_type} ${r.operator} ${r.threshold_value} → ${r.action}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
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
        alert("تمت المراجعة");
      });
    }
    OrionAdminFraud.loadRules();
  },
};