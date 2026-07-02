/** Search merchandising admin — synonyms, redirects, boosts. */
const OrionAdminSearch = {
  async loadSynonyms() {
    const el = document.getElementById("search-synonyms-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/search/synonyms");
      const rows = data.synonyms || [];
      if (!rows.length) { el.textContent = "لا توجد مرادفات."; return; }
      el.innerHTML = rows.map((s) =>
        `<div class="border-b py-2"><strong>${s.term}</strong> → ${(s.synonyms || []).join(", ")}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadRedirects() {
    const el = document.getElementById("search-redirects-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/search/redirects");
      const rows = data.redirects || [];
      if (!rows.length) { el.textContent = "لا توجد توجيهات."; return; }
      el.innerHTML = rows.map((r) =>
        `<div class="border-b py-2">${r.query_term} → <a href="${r.redirect_url}" class="text-blue-600" target="_blank">${r.redirect_url}</a></div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async loadBoosts() {
    const el = document.getElementById("search-boosts-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/search/boosts");
      const rows = data.boosts || [];
      if (!rows.length) { el.textContent = "لا توجد قواعد تعزيز."; return; }
      el.innerHTML = rows.map((b) =>
        `<div class="border-b py-2">product=${b.product_id || '-'} cat=${b.category_id || '-'} kw=${b.query_keyword || '-'} ×${b.boost_factor}</div>`
      ).join("");
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const synForm = document.getElementById("search-synonym-form");
    if (synForm) {
      synForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(synForm);
        await OrionAPI.post("/search/synonyms", {
          term: fd.get("term"), synonyms: (fd.get("synonyms") || "").split(",").map((s) => s.trim()).filter(Boolean),
        });
        synForm.reset();
        OrionAdminSearch.loadSynonyms();
      });
    }
    const redForm = document.getElementById("search-redirect-form");
    if (redForm) {
      redForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(redForm);
        await OrionAPI.post("/search/redirects", { query_term: fd.get("query_term"), redirect_url: fd.get("redirect_url") });
        redForm.reset();
        OrionAdminSearch.loadRedirects();
      });
    }
    const boostForm = document.getElementById("search-boost-form");
    if (boostForm) {
      boostForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(boostForm);
        const payload = { boost_factor: parseInt(fd.get("boost_factor") || "1") };
        const pid = fd.get("product_id"); if (pid) payload.product_id = parseInt(pid);
        const cid = fd.get("category_id"); if (cid) payload.category_id = parseInt(cid);
        const kw = fd.get("query_keyword"); if (kw) payload.query_keyword = kw;
        await OrionAPI.post("/search/boosts", payload);
        boostForm.reset();
        OrionAdminSearch.loadBoosts();
      });
    }
    OrionAdminSearch.loadSynonyms();
    OrionAdminSearch.loadRedirects();
    OrionAdminSearch.loadBoosts();
  },
};