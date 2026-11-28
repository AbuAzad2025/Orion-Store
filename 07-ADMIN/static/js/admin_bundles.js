/** Bundle management — create, edit, publish, add items. */
const OrionAdminBundles = {
  resetBundleForm() {
    const bundleSelect = document.getElementById("bundle-item-bundle");
    if (bundleSelect) bundleSelect.addEventListener("change", () => OrionAdminBundles.loadBundleItems(bundleSelect.value));
    const form = document.getElementById("bundle-form");
    if (!form) return;
    form.reset();
    const id = document.getElementById("bundle-edit-id");
    const submit = document.getElementById("bundle-submit");
    const cancel = document.getElementById("bundle-cancel-edit");
    if (id) id.value = "";
    if (submit) submit.textContent = OrionI18n.t("إضافة حزمة", "Add bundle");
    if (cancel) cancel.classList.add("hidden");
  },

  async loadBundles() {
    const el = document.getElementById("bundles-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/bundles");
      const rows = data.bundles || [];
      if (!rows.length) { el.textContent = OrionI18n.t("لا توجد حزم بعد.", "No bundles yet."); return; }
      SafeDOM.clear(el);
      const select = document.getElementById("bundle-item-bundle");
      if (select) {
        const current = select.value;
        SafeDOM.clear(select);
        select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر حزمة…", "Choose a bundle…")]));
        for (const b of rows) select.appendChild(SafeDOM.elem("option", { value: b.id }, [`#${b.id} — ${b.name}`]));
        select.value = current;
      }
      for (const b of rows) {
        const editBtn = SafeDOM.actionBtn(
          OrionI18n.t("تعديل", "Edit"), "orion-btn text-xs", () => {
            const form = document.getElementById("bundle-form");
            if (!form) return;
            const set = (name, value) => { const f = form.querySelector(`[name="${name}"]`); if (f) f.value = value ?? ""; };
            set("name", b.name); set("name_en", b.name_en); set("slug", b.slug);
            set("bundle_price", b.bundle_price); set("description", b.description);
            set("image_url", b.image_url); set("max_per_order", b.max_per_order);
            const pub = form.querySelector('[name="is_published"]');
            if (pub) pub.checked = !!b.is_published;
            const id = document.getElementById("bundle-edit-id");
            const submit = document.getElementById("bundle-submit");
            const cancel = document.getElementById("bundle-cancel-edit");
            if (id) id.value = b.id;
            if (submit) submit.textContent = OrionI18n.t("حفظ التعديلات", "Save changes");
            if (cancel) cancel.classList.remove("hidden");
            form.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        );
        const pubBtn = SafeDOM.actionBtn(
          b.is_published ? OrionI18n.t("إلغاء النشر", "Unpublish") : OrionI18n.t("نشر", "Publish"),
          "orion-btn text-xs",
          async () => {
            try {
              await OrionAPI.put(`/bundles/${b.id}`, { is_published: !b.is_published });
              OrionAdminBundles.loadBundles();
            } catch (err) { OrionUI.toast(err.message, "error"); }
          }
        );
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex items-center justify-between gap-2 flex-wrap" }, [
          SafeDOM.elem("span", null, [
            SafeDOM.elem("strong", null, [b.name]),
            ` (${b.slug}) — ${OrionUI.money(b.bundle_price, b.currency || "")}`
          ]),
          SafeDOM.elem("div", { className: "flex gap-2" }, [editBtn, pubBtn])
        ]));
      }
    } catch (err) { el.textContent = err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"); }
  },

  async loadBundleItems(bundleId) {
    const el = document.getElementById("bundle-items-list");
    if (!el) return;
    if (!bundleId) {
      SafeDOM.clear(el);
      SafeDOM.text(el, OrionI18n.t("اختر حزمة لعرض أصنافها.", "Choose a bundle to see its items."));
      return;
    }
    try {
      SafeDOM.clear(el);
      SafeDOM.text(el, OrionI18n.t("جارٍ التحميل…", "Loading…"));
      const data = await OrionAPI.get(`/bundles/${bundleId}/items`);
      SafeDOM.clear(el);
      const rows = data.items || [];
      if (!rows.length) {
        SafeDOM.text(el, OrionI18n.t("لا توجد أصناف في هذه الحزمة.", "No items in this bundle."));
        return;
      }
      for (const item of rows) {
        const qty = SafeDOM.elem("input", {
          type: "number", min: "1", step: "1", value: String(item.quantity),
          className: "orion-input w-20",
          "aria-label": OrionI18n.t("الكمية", "Quantity"),
        });
        const discount = SafeDOM.elem("input", {
          type: "number", min: "0", max: "100", step: "0.01",
          value: String(item.discount_percent),
          className: "orion-input w-20",
          "aria-label": OrionI18n.t("خصم %", "Discount %"),
        });
        const save = SafeDOM.actionBtn(
          OrionI18n.t("حفظ", "Save"), "orion-btn text-xs", async () => {
            const quantity = Number(qty.value);
            const percent = discount.value === "" ? "0" : String(discount.value);
            if (!Number.isInteger(quantity) || quantity < 1) {
              OrionUI.toast(OrionI18n.t("الكمية يجب أن تكون 1 على الأقل", "Quantity must be at least 1"), "error");
              return;
            }
            if (!(Number(percent) >= 0 && Number(percent) <= 100)) {
              OrionUI.toast(OrionI18n.t("الخصم يجب أن يكون بين 0 و 100", "Discount must be between 0 and 100"), "error");
              return;
            }
            try {
              await OrionAPI.put(`/bundles/${bundleId}/items/${item.id}`, {
                quantity, discount_percent: percent,
              });
              OrionUI.toast(OrionI18n.t("تم حفظ الصنف", "Item saved"), "success");
              OrionAdminBundles.loadBundleItems(bundleId);
            } catch (err) { OrionUI.toast(err.message, "error"); }
          }
        );
        const remove = SafeDOM.actionBtn(
          OrionI18n.t("حذف", "Delete"), "orion-btn text-xs", async () => {
            if (!OrionUI.confirmDanger(OrionI18n.t("حذف الصنف من الحزمة؟", "Delete this item from the bundle?"))) return;
            try {
              await OrionAPI.delete(`/bundles/${bundleId}/items/${item.id}`);
              OrionUI.toast(OrionI18n.t("تم حذف الصنف", "Item deleted"), "success");
              OrionAdminBundles.loadBundleItems(bundleId);
            } catch (err) { OrionUI.toast(err.message, "error"); }
          }
        );
        el.appendChild(SafeDOM.elem(
          "div",
          { className: "border-b py-2 flex items-center justify-between gap-2 flex-wrap" },
          [
            SafeDOM.elem("span", null, [`#${item.product_id}`]),
            SafeDOM.elem("div", { className: "flex gap-2 items-center" }, [qty, discount, save, remove]),
          ]
        ));
      }
    } catch (err) {
      SafeDOM.clear(el);
      SafeDOM.text(el, err.message || OrionI18n.t("تعذّر التحميل", "Failed to load"));
    }
  },

  async loadBundleProducts() {
    const select = document.getElementById("bundle-item-product");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/oms/products");
      const current = select.value;
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t("اختر منتجاً…", "Choose a product…")]));
      for (const p of data.products || []) {
        select.appendChild(SafeDOM.elem("option", { value: p.id }, [`#${p.id} — ${p.name}`]));
      }
      select.value = current;
    } catch (err) { /* keep empty */ }
  },

  init() {
    const form = document.getElementById("bundle-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const fd = new FormData(form);
          const id = document.getElementById("bundle-edit-id")?.value;
          const payload = {
            name: fd.get("name"), name_en: fd.get("name_en") || undefined, slug: fd.get("slug"),
            bundle_price: String(fd.get("bundle_price") || "0"),
            description: fd.get("description") || undefined,
            image_url: fd.get("image_url") || undefined,
            max_per_order: fd.get("max_per_order") ? Number(fd.get("max_per_order")) : null,
            is_published: fd.get("is_published") === "on",
          };
          if (id) await OrionAPI.put(`/bundles/${id}`, payload);
          else await OrionAPI.post("/bundles", payload);
          const msg = document.getElementById("bundle-form-msg");
          if (msg) msg.textContent = OrionI18n.t(id ? "تم حفظ الحزمة" : "تمت إضافة الحزمة", id ? "Bundle saved" : "Bundle added");
          OrionAdminBundles.resetBundleForm();
          OrionAdminBundles.loadBundles();
        } catch (err) {
          const msg = document.getElementById("bundle-form-msg");
          if (msg) msg.textContent = err.message;
          OrionUI.toast(err.message, "error");
        }
      });
    }
    const cancel = document.getElementById("bundle-cancel-edit");
    if (cancel) cancel.addEventListener("click", () => OrionAdminBundles.resetBundleForm());
    const itemForm = document.getElementById("bundle-item-form");
    if (itemForm) {
      itemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(itemForm);
        const msg = document.getElementById("bundle-item-msg");
        try {
          await OrionAPI.post(`/bundles/${fd.get("bundle_id")}/items`, {
            product_id: Number(fd.get("product_id")),
            quantity: Number(fd.get("quantity") || 1),
            discount_percent: String(fd.get("discount_percent") || "0"),
          });
          if (msg) msg.textContent = OrionI18n.t("تمت إضافة الصنف", "Item added");
          const bundleId = fd.get("bundle_id");
          itemForm.reset();
          if (bundleSelect) bundleSelect.value = bundleId;
          OrionAdminBundles.loadBundleItems(bundleId);
        } catch (err) {
          if (msg) msg.textContent = err.message;
        }
      });
    }
    OrionAdminBundles.loadBundleProducts();
    OrionAdminBundles.loadBundles();
  },
};
