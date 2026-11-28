/** Full product management for tenant admins — SafeDOM + OrionAPI. */
function orionSignedImageUrl(url) {
  if (!url) return "";
  const base = String(url).split("?")[0];
  const token = document.body.dataset.storeToken || "";
  return token ? `${base}?store=${encodeURIComponent(token)}` : base;
}

const OrionAdminProducts = {
  async loadCategories() {
    const select = document.getElementById("p-category");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/categories/");
      const current = select.value;
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t('بدون تصنيف', 'No category')]));
      for (const category of data.categories || []) {
        select.appendChild(
          SafeDOM.elem("option", { value: category.id }, [category.name])
        );
      }
      select.value = current;
    } catch (err) {
      OrionUI.toast(err.message, "error");
    }
  },

  async loadBrands() {
    const select = document.getElementById("p-brand");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/brands/");
      const current = select.value;
      SafeDOM.clear(select);
      select.appendChild(SafeDOM.elem("option", { value: "" }, [OrionI18n.t('بدون علامة', 'No brand')]));
      for (const brand of data.brands || []) {
        select.appendChild(SafeDOM.elem("option", { value: brand.id }, [brand.name]));
      }
      select.value = current;
    } catch (err) { /* brands API optional — leave empty */ }
  },

  async loadProducts() {
    const list = document.getElementById("products-list");
    if (!list) return;
    try {
      const data = await OrionAPI.get("/products/");
      const products = data.products || [];
      SafeDOM.clear(list);
      if (!products.length) {
        list.appendChild(SafeDOM.elem("p", { className: "orion-muted" }, [OrionI18n.t('لا توجد منتجات بعد.', 'No products yet.')]));
        return;
      }
      for (const product of products) {
        const thumb = product.image_url
          ? SafeDOM.elem("img", {
              src: orionSignedImageUrl(product.image_url),
              alt: product.name,
              className: "w-12 h-12 object-cover rounded border border-slate-700",
            })
          : SafeDOM.elem("span", { className: "orion-muted text-xs" }, [OrionI18n.t('لا صورة', 'No image')]);
        const info = SafeDOM.elem("div", { className: "flex-1" }, [
          SafeDOM.elem("div", { className: "font-semibold" }, [product.name]),
          SafeDOM.elem("div", { className: "orion-muted text-xs" }, [
            `${OrionUI.money(product.price)} · ${OrionI18n.t('مخزون', 'Stock')}: ${product.quantity} · ${product.is_published ? OrionI18n.t('منشور', 'Published') : OrionI18n.t('مخفي', 'Hidden')}`,
          ]),
        ]);
        const edit = SafeDOM.actionBtn(OrionI18n.t('تعديل', 'Edit'), "orion-btn", () => this.fillForm(product));
        const remove = SafeDOM.actionBtn(OrionI18n.t('حذف', 'Delete'), "orion-btn", async () => {
          if (!OrionUI.confirmDanger(`${OrionI18n.t('حذف', 'Delete')} "${product.name}"?`)) return;
          try {
            await OrionAPI.delete(`/products/${product.public_id}`);
            OrionUI.toast(OrionI18n.t('تم حذف المنتج', 'Product deleted'), "success");
            this.loadProducts();
          } catch (err) {
            OrionUI.toast(err.message, "error");
          }
        });
        list.appendChild(
          SafeDOM.elem("div", { className: "flex items-center gap-3 border-b border-slate-800 py-2" }, [
            thumb,
            info,
            edit,
            remove,
          ])
        );
      }
    } catch (err) {
      OrionUI.toast(err.message, "error");
    }
  },

  fillForm(product) {
    OrionUI.set("product-edit-id", product.public_id || "");
    OrionUI.set("form-title", OrionI18n.t('تعديل المنتج', 'Edit product'), "textContent");
    OrionUI.set("p-name", product.name || "");
    OrionUI.set("p-slug", product.slug || "");
    OrionUI.set("p-price", product.price || "");
    OrionUI.set("p-cost", product.cost_price || "0");
    OrionUI.set("p-quantity", product.quantity ?? 0);
    OrionUI.set("p-sku", product.sku || "");
    OrionUI.set("p-category", product.category_id || "");
    OrionUI.set("p-brand", product.brand_id || "");
    OrionUI.set("p-compare", product.compare_at_price || "");
    OrionUI.set("p-description", product.description || "");
    OrionUI.set("p-image", product.image_url || "");
    OrionUI.set("p-short", product.short_description || "");
    OrionUI.set("p-published", Boolean(product.is_published), "checked");
    OrionUI.set("p-featured", Boolean(product.is_featured), "checked");
  },

  clearForm() {
    document.getElementById("product-form")?.reset();
    OrionUI.set("product-edit-id", "");
    OrionUI.set("form-title", OrionI18n.t('إضافة منتج', 'Add product'), "textContent");
    OrionUI.set("p-quantity", "0");
    const cost = document.getElementById("p-cost");
    if (cost) cost.value = "0";
  },

  payload() {
    return {
      name: OrionUI.val("p-name").trim(),
      slug: OrionUI.val("p-slug").trim(),
      price: OrionUI.val("p-price"),
      cost_price: OrionUI.val("p-cost") || "0",
      quantity: parseInt(OrionUI.val("p-quantity") || "0", 10),
      sku: OrionUI.val("p-sku").trim() || null,
      category_id: OrionUI.val("p-category") || null,
      brand_id: OrionUI.val("p-brand") || null,
      compare_at_price: OrionUI.val("p-compare") || null,
      description: OrionUI.val("p-description").trim() || null,
      image_url: OrionUI.val("p-image").trim() || null,
      short_description: OrionUI.val("p-short").trim() || null,
      is_published: OrionUI.checked("p-published"),
      is_featured: OrionUI.checked("p-featured"),
    };
  },

  async init() {
    const form = document.getElementById("product-form");
    if (!form) return;
    // Lookup options must exist before Edit can preselect category/brand.
    await this.loadCategories();
    await this.loadBrands();
    this.loadProducts();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const msg = document.getElementById("product-msg");
      const editId = OrionUI.val("product-edit-id");
      if (!(await orionUploadProductImage())) return;
      const body = this.payload();
      try {
        await OrionUI.withLoading(form, () =>
          editId
            ? OrionAPI.put(`/products/${editId}`, body)
            : OrionAPI.post("/products/", body)
        );
        this.clearForm();
        msg.textContent = editId ? OrionI18n.t('تم تعديل المنتج', 'Product updated') : OrionI18n.t('تمت إضافة المنتج', 'Product added');
        OrionUI.toast(msg.textContent, "success");
        this.loadProducts();
      } catch (err) {
        msg.textContent = err.message;
        OrionUI.toast(err.message, "error");
      }
    });

    document.getElementById("btn-cancel")?.addEventListener("click", () => this.clearForm());
    document.getElementById("btn-refresh")?.addEventListener("click", () => this.loadProducts());
  },
};
