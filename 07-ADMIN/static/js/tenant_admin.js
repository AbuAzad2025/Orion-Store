/** Tenant admin page loaders (wave 5 #52-53). */
document.addEventListener("DOMContentLoaded", () => {
  const statsEl = document.getElementById("tenant-stats");
  if (statsEl) {
    OrionAPI.get("/tenant/dashboard")
      .then((data) => {
        const s = data.stats;
        statsEl.innerHTML = `
          <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">الطلبات</p><p class="text-2xl font-bold">${s.orders_total}</p></div>
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">مدفوعة</p><p class="text-2xl font-bold">${s.orders_paid}</p></div>
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">المنتجات</p><p class="text-2xl font-bold">${s.products_total}</p></div>
            <div class="rounded-lg bg-white p-4 shadow"><p class="text-sm text-gray-500">منشورة</p><p class="text-2xl font-bold">${s.products_published}</p></div>
          </div>`;
      })
      .catch((err) => {
        statsEl.textContent = err.message;
      });
  }

  const gatewaysEl = document.getElementById("gateways-list");
  if (gatewaysEl) {
    OrionAPI.get("/tenant/gateways")
      .then((data) => {
        if (!data.gateways.length) {
          gatewaysEl.innerHTML = "<p class='text-gray-500'>لا توجد بوابات.</p>";
          return;
        }
        gatewaysEl.innerHTML = data.gateways
          .map(
            (g) =>
              `<div class="rounded border p-3 mb-2"><strong>${g.display_name}</strong> (${g.provider}) — ${g.status}</div>`
          )
          .join("");
      })
      .catch((err) => {
        gatewaysEl.textContent = err.message;
      });
  }

  const codBtn = document.getElementById("enable-cod");
  if (codBtn) {
    codBtn.addEventListener("click", () => {
      OrionAPI.post("/tenant/gateways/cod")
        .then(() => location.reload())
        .catch((err) => alert(err.message));
    });
  }

  const paypalBtn = document.getElementById("connect-paypal");
  if (paypalBtn) {
    paypalBtn.addEventListener("click", () => {
      const clientId = document.getElementById("paypal-client-id").value.trim();
      const clientSecret = document.getElementById("paypal-client-secret").value.trim();
      const isSandbox = document.getElementById("paypal-sandbox").checked;
      OrionAPI.post("/tenant/gateways/paypal", {
        client_id: clientId,
        client_secret: clientSecret,
        is_sandbox: isSandbox,
        is_enabled: true,
      })
        .then(() => {
          alert("تم ربط PayPal");
          location.reload();
        })
        .catch((err) => alert(err.message));
    });
  }

  const bnplEl = document.getElementById("bnpl-providers-list");
  if (bnplEl) {
    OrionAPI.get("/tenant/bnpl/providers")
      .then((data) => {
        bnplEl.innerHTML = (data.providers || [])
          .map(
            (p) => `
          <div class="rounded border p-3 mb-3 bg-gray-50" data-bnpl="${p.provider}">
            <div class="flex justify-between items-center mb-2">
              <strong>${p.provider}</strong>
              <span class="text-xs ${p.is_enabled ? "text-green-700" : "text-gray-500"}">
                ${p.is_enabled ? "مفعّل" : "معطّل"}
              </span>
            </div>
            <input type="text" class="bnpl-merchant border rounded px-2 py-1 text-sm w-full mb-2"
              placeholder="Merchant ID" value="${p.merchant_id || ""}">
            <input type="password" class="bnpl-key border rounded px-2 py-1 text-sm w-full mb-2"
              placeholder="API Key (اتركه فارغاً للإبقاء)">
            <label class="inline-flex items-center gap-2 text-sm mb-2">
              <input type="checkbox" class="bnpl-sandbox" ${(p.config || {}).is_sandbox !== false ? "checked" : ""}>
              Sandbox
            </label>
            <button type="button" class="bnpl-save rounded bg-indigo-600 px-3 py-1 text-white text-sm"
              data-provider="${p.provider}">حفظ</button>
          </div>`
          )
          .join("");
        bnplEl.querySelectorAll(".bnpl-save").forEach((btn) => {
          btn.addEventListener("click", () => {
            const code = btn.getAttribute("data-provider");
            const wrap = btn.closest(`[data-bnpl="${code}"]`);
            OrionAPI.put(`/tenant/bnpl/providers/${code}`, {
              merchant_id: wrap.querySelector(".bnpl-merchant").value.trim(),
              api_key: wrap.querySelector(".bnpl-key").value.trim() || undefined,
              is_enabled: true,
              is_sandbox: wrap.querySelector(".bnpl-sandbox").checked,
            })
              .then(() => {
                alert("تم الحفظ");
                location.reload();
              })
              .catch((err) => alert(err.message));
          });
        });
      })
      .catch((err) => {
        bnplEl.textContent = err.message;
      });
  }

  const templatesEl = document.getElementById("templates-list");
  if (templatesEl) {
    OrionAPI.get("/tenant/document-templates")
      .then((data) => {
        if (!data.templates.length) {
          templatesEl.innerHTML = "<p class='text-gray-500'>لا توجد قوالب بعد.</p>";
          return;
        }
        templatesEl.innerHTML = data.templates
          .map(
            (t) =>
              `<div class="rounded border p-3 mb-2"><strong>${t.document_type}</strong> (${t.locale})</div>`
          )
          .join("");
      })
      .catch((err) => {
        templatesEl.textContent = err.message;
      });
  }

  const saveBtn = document.getElementById("save-invoice-template");
  if (saveBtn) {
    saveBtn.addEventListener("click", () => {
      const body = document.getElementById("invoice-body").value;
      OrionAPI.put("/tenant/document-templates/invoice", { body_html: body })
        .then(() => alert("تم الحفظ"))
        .catch((err) => alert(err.message));
    });
  }

  const flagsEl = document.getElementById("feature-flags-list");
  if (flagsEl) {
    OrionAPI.get("/tenant/feature-flags")
      .then((data) => {
        flagsEl.innerHTML = data.flags
          .map(
            (f) => `
          <div class="rounded border p-3 bg-white" data-flag="${f.code}">
            <div class="flex items-center justify-between">
              <div>
                <strong>${f.name}</strong>
                <p class="text-xs text-gray-500">${f.code} — ${f.description || ""}</p>
                <p class="text-xs text-gray-400 mt-1">Rollout: ${f.rollout_percent}%</p>
              </div>
              <div class="flex items-center gap-3">
                ${f.has_override ? `<span class="text-xs text-amber-600">مخصّص</span>` : `<span class="text-xs text-gray-400">تلقائي</span>`}
                <label class="inline-flex items-center gap-2">
                  <input type="checkbox" data-flag-code="${f.code}" ${f.value ? "checked" : ""}>
                  <span class="text-sm">${f.value ? "مفعّل" : "معطّل"}</span>
                </label>
              </div>
            </div>
            ${f.override_reason ? `<div class="mt-2 text-xs text-gray-500 border-t pt-2"><span class="font-medium">السبب:</span> ${f.override_reason}${f.override_set_by_name ? ` <span class="text-gray-400 mr-2">— ${f.override_set_by_name}</span>` : ""}</div>` : ""}
            ${f.has_override ? `<div class="mt-2 text-right"><button class="remove-override text-xs text-red-500" data-flag-code="${f.code}">إزالة التخصيص</button></div>` : ""}
            <div class="reason-field mt-2 hidden" data-flag-code="${f.code}">
              <input type="text" class="reason-input w-full border rounded px-2 py-1 text-xs" placeholder="سبب التغيير (اختياري)">
              <button class="save-override mt-1 text-xs rounded bg-blue-600 px-3 py-1 text-white" data-flag-code="${f.code}">حفظ مع السبب</button>
            </div>
          </div>`
          )
          .join("");
        flagsEl.querySelectorAll("input[data-flag-code]").forEach((input) => {
          input.addEventListener("change", () => {
            const code = input.getAttribute("data-flag-code");
            const container = document.querySelector(`[data-flag="${code}"]`);
            const reasonField = container.querySelector(".reason-field");
            if (input.checked !== (container.querySelector(".save-override") !== null)) {
              reasonField.classList.remove("hidden");
            }
          });
        });
        flagsEl.querySelectorAll(".save-override").forEach((btn) => {
          btn.addEventListener("click", () => {
            const code = btn.getAttribute("data-flag-code");
            const container = document.querySelector(`[data-flag="${code}"]`);
            const checkbox = container.querySelector("input[data-flag-code]");
            const reason = container.querySelector(".reason-input").value.trim() || null;
            OrionAPI.put(`/tenant/feature-flags/${code}`, { value: checkbox.checked, reason })
              .then(() => location.reload())
              .catch((err) => alert(err.message));
          });
        });
        flagsEl.querySelectorAll(".remove-override").forEach((btn) => {
          btn.addEventListener("click", () => {
            const code = btn.getAttribute("data-flag-code");
            if (!confirm("إزالة التخصيص لهذه الميزة؟")) return;
            OrionAPI.put(`/tenant/feature-flags/${code}`, { value: null })
              .then(() => location.reload())
              .catch((err) => alert(err.message));
          });
        });
      })
      .catch((err) => {
        flagsEl.textContent = err.message;
      });
  }
});
