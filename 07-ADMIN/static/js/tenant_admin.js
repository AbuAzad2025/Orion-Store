/** Tenant admin page loaders (wave 5 #52-53). */
document.addEventListener("DOMContentLoaded", () => {
  const statsEl = document.getElementById("tenant-stats");
  if (statsEl) {
    OrionAPI.get("/tenant/dashboard")
      .then((data) => {
        const s = data.stats;
        SafeDOM.clear(statsEl);
        statsEl.appendChild(SafeDOM.elem("div", { className: "grid grid-cols-2 gap-4 md:grid-cols-4" }, [
          SafeDOM.elem("div", { className: "orion-card orion-stat" }, [
            SafeDOM.elem("p", { className: "orion-stat-label" }, ["الطلبات"]),
            SafeDOM.elem("p", { className: "orion-stat-value" }, [Number(s.orders_total || 0).toLocaleString("ar")])
          ]),
          SafeDOM.elem("div", { className: "orion-card orion-stat" }, [
            SafeDOM.elem("p", { className: "orion-stat-label" }, ["مدفوعة"]),
            SafeDOM.elem("p", { className: "orion-stat-value" }, [Number(s.orders_paid || 0).toLocaleString("ar")])
          ]),
          SafeDOM.elem("div", { className: "orion-card orion-stat" }, [
            SafeDOM.elem("p", { className: "orion-stat-label" }, ["المنتجات"]),
            SafeDOM.elem("p", { className: "orion-stat-value" }, [Number(s.products_total || 0).toLocaleString("ar")])
          ]),
          SafeDOM.elem("div", { className: "orion-card orion-stat" }, [
            SafeDOM.elem("p", { className: "orion-stat-label" }, ["منشورة"]),
            SafeDOM.elem("p", { className: "orion-stat-value" }, [Number(s.products_published || 0).toLocaleString("ar")])
          ])
        ]));
      })
      .catch((err) => {
        statsEl.textContent = err.message;
      });
  }

  const methodsEl = document.getElementById("payment-methods-list");
  if (methodsEl) {
    OrionAPI.get("/tenant/payment-methods")
      .then((data) => {
        SafeDOM.clear(methodsEl);
        data.methods.forEach((m) => {
          const toggle = SafeDOM.elem("input", { type: "checkbox", className: "pm-toggle" });
          if (m.is_enabled) toggle.checked = "";
          const nameInput = SafeDOM.elem("input", {
            type: "text", className: "pm-name border rounded px-2 py-1 text-sm w-full mb-2",
            value: m.display_name || m.label
          });
          const parts = [
            SafeDOM.elem("label", { className: "inline-flex items-center gap-2 font-medium text-sm" }, [
              toggle, m.label
            ])
          ];
          if (!m.needs_credentials) {
            const notes = SafeDOM.elem("textarea", {
              className: "pm-notes border rounded px-2 py-1 text-sm w-full mb-2",
              rows: "2", placeholder: "تعليمات تظهر للزبون عند الدفع"
            });
            notes.value = m.instructions || "";
            parts.push(notes);
          }
          const status = SafeDOM.elem("span", { className: "pm-status text-xs text-gray-500" }, [m.is_enabled ? "مفعّل" : "معطّل"]);
          const save = SafeDOM.elem("button", { type: "button", className: "pm-save rounded bg-emerald-600 px-3 py-1 text-white text-sm", "data-code": m.code }, ["حفظ"]);
          parts.push(nameInput, status, save);
          methodsEl.appendChild(SafeDOM.elem("div", { className: "rounded border p-3 bg-gray-50", "data-method": m.code }, parts));
        });
        methodsEl.querySelectorAll(".pm-toggle").forEach((el) => {
          el.addEventListener("change", () => {
            const wrap = el.closest("[data-method]");
            wrap.querySelector(".pm-status").textContent = el.checked ? "مفعّل" : "معطّل";
          });
        });
        methodsEl.querySelectorAll(".pm-save").forEach((btn) => {
          btn.addEventListener("click", () => {
            const wrap = btn.closest("[data-method]");
            const notes = wrap.querySelector(".pm-notes");
            OrionAPI.post("/tenant/payment-methods", {
              code: btn.dataset.code,
              display_name: wrap.querySelector(".pm-name").value.trim(),
              instructions: notes ? notes.value.trim() : "",
              is_enabled: wrap.querySelector(".pm-toggle").checked
            }).then(() => {
              btn.textContent = "تم الحفظ";
              setTimeout(() => { btn.textContent = "حفظ"; }, 1500);
            }).catch((err) => alert(err.message));
          });
        });
      })
      .catch((err) => {
        methodsEl.textContent = err.message;
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
        SafeDOM.clear(bnplEl);
        (data.providers || []).forEach((p) => {
          const sandboxAttrs = { type: "checkbox", className: "bnpl-sandbox" };
          if ((p.config || {}).is_sandbox !== false) sandboxAttrs.checked = "";
          const wrap = SafeDOM.elem("div", { className: "rounded border p-3 mb-3 bg-gray-50", "data-bnpl": p.provider }, [
            SafeDOM.elem("div", { className: "flex justify-between items-center mb-2" }, [
              SafeDOM.elem("strong", null, [p.provider]),
              SafeDOM.elem("span", { className: `text-xs ${p.is_enabled ? "text-green-700" : "text-gray-500"}` }, [p.is_enabled ? "مفعّل" : "معطّل"])
            ]),
            SafeDOM.elem("input", { type: "text", className: "bnpl-merchant border rounded px-2 py-1 text-sm w-full mb-2", placeholder: "Merchant ID", value: p.merchant_id || "" }),
            SafeDOM.elem("input", { type: "password", className: "bnpl-key border rounded px-2 py-1 text-sm w-full mb-2", placeholder: "API Key (اتركه فارغاً للإبقاء)" }),
            SafeDOM.elem("label", { className: "inline-flex items-center gap-2 text-sm mb-2" }, [
              SafeDOM.elem("input", sandboxAttrs),
              " وضع الاختبار"
            ]),
            SafeDOM.elem("button", { type: "button", className: "bnpl-save rounded bg-indigo-600 px-3 py-1 text-white text-sm", "data-provider": p.provider }, ["حفظ"])
          ]);
          bnplEl.appendChild(wrap);
        });
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
          SafeDOM.clear(templatesEl);
          templatesEl.appendChild(SafeDOM.emptyMsg("لا توجد قوالب بعد."));
          return;
        }
        SafeDOM.clear(templatesEl);
        data.templates.forEach((t) => {
          templatesEl.appendChild(SafeDOM.elem("div", { className: "rounded border p-3 mb-2" }, [
            SafeDOM.elem("strong", null, [t.document_type]),
            ` (${t.locale})`
          ]));
        });
      })
      .catch((err) => {
        templatesEl.textContent = err.message;
      });
  }

  const saveBtn = document.getElementById("save-invoice-template");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const body = document.getElementById("invoice-body").value;
      const msg = document.getElementById("invoice-msg");
      try {
        await OrionUI.withLoading(saveBtn, () =>
          OrionAPI.put("/tenant/document-templates/invoice", { body_html: body })
        );
        if (msg) msg.textContent = "تم حفظ القالب بنجاح";
        OrionAPI.get("/tenant/document-templates").then((data) => {
          const el = document.getElementById("templates-list");
          if (!el) return;
          SafeDOM.clear(el);
          (data.templates || []).forEach((t) => {
            el.appendChild(SafeDOM.elem("div", { className: "border-b py-1" }, [
              SafeDOM.elem("strong", null, [t.document_type]), ` (${t.locale})`
            ]));
          });
        });
      } catch (err) {
        if (msg) msg.textContent = err.message;
      }
    });
  }

  const flagsEl = document.getElementById("feature-flags-list");
  const flagNamesAr = {
    ai_enabled: "المساعد الذكي",
    booking_enabled: "الحجوزات",
    multi_language: "تعدد اللغات",
    subscriptions_enabled: "الاشتراكات",
    bopis_enabled: "الاستلام من المتجر",
    store_credit_enabled: "رصيد المتجر",
    draft_orders_enabled: "الطلبات المسودة",
    affiliates_enabled: "المسوقون",
    gift_registries_enabled: "قوائم الهدايا",
    dropship_enabled: "الدروبشيبنج",
    live_chat_enabled: "الدردشة المباشرة"
  };
  if (flagsEl) {
    OrionAPI.get("/tenant/feature-flags")
      .then((data) => {
        SafeDOM.clear(flagsEl);
        data.flags.forEach((f) => {
          const checkboxAttrs = { type: "checkbox", "data-flag-code": f.code };
          if (f.value) checkboxAttrs.checked = "";
          const overrideSection = f.override_reason ? SafeDOM.elem("div", { className: "mt-2 text-xs text-gray-500 border-t pt-2" }, [
            SafeDOM.elem("span", { className: "font-medium" }, ["السبب:"]),
            ` ${f.override_reason}`,
            f.override_set_by_name ? SafeDOM.elem("span", { className: "text-gray-400 mr-2" }, [`— ${f.override_set_by_name}`]) : null
          ]) : null;
          const removeSection = f.has_override ? SafeDOM.elem("div", { className: "mt-2 text-right" }, [
            SafeDOM.elem("button", { className: "remove-override text-xs text-red-500", "data-flag-code": f.code }, ["إزالة التخصيص"])
          ]) : null;
          const flagWrap = SafeDOM.elem("div", { className: "rounded border p-3 bg-white", "data-flag": f.code }, [
            SafeDOM.elem("div", { className: "flex items-center justify-between" }, [
              SafeDOM.elem("div", null, [
                SafeDOM.elem("strong", null, [flagNamesAr[f.code] || f.name]),
                SafeDOM.elem("p", { className: "text-xs text-gray-500" }, [`${f.code} — ${f.description || ""}`]),
                SafeDOM.elem("p", { className: "text-xs text-gray-400 mt-1" }, [`نسبة النشر: ${f.rollout_percent}%`])
              ]),
              SafeDOM.elem("div", { className: "flex items-center gap-3" }, [
                f.has_override ? SafeDOM.elem("span", { className: "text-xs text-amber-600" }, ["مخصّص"]) : SafeDOM.elem("span", { className: "text-xs text-gray-400" }, ["تلقائي"]),
                SafeDOM.elem("label", { className: "inline-flex items-center gap-2" }, [
                  SafeDOM.elem("input", checkboxAttrs),
                  SafeDOM.elem("span", { className: "text-sm" }, [f.value ? "مفعّل" : "معطّل"])
                ])
              ])
            ]),
            overrideSection,
            removeSection,
            SafeDOM.elem("div", { className: "reason-field mt-2 hidden", "data-flag-code": f.code }, [
              SafeDOM.elem("input", { type: "text", className: "reason-input w-full border rounded px-2 py-1 text-xs", placeholder: "سبب التغيير (اختياري)" }),
              SafeDOM.elem("button", { className: "save-override mt-1 text-xs rounded bg-blue-600 px-3 py-1 text-white", "data-flag-code": f.code }, ["حفظ مع السبب"])
            ])
          ]);
          flagsEl.appendChild(flagWrap);
        });
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
