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
            `${product.price} ₪ · ${OrionI18n.t('مخزون', 'Stock')}: ${product.quantity} · ${product.is_published ? OrionI18n.t('منشور', 'Published') : OrionI18n.t('مخفي', 'Hidden')}`,
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
    document.getElementById("product-edit-id").value = product.public_id || "";
    document.getElementById("form-title").textContent = OrionI18n.t('تعديل المنتج', 'Edit product');
    document.getElementById("p-name").value = product.name || "";
    document.getElementById("p-slug").value = product.slug || "";
    document.getElementById("p-price").value = product.price || "";
    document.getElementById("p-quantity").value = product.quantity ?? 0;
    document.getElementById("p-sku").value = product.sku || "";
    document.getElementById("p-category").value = product.category_id || "";
    document.getElementById("p-brand").value = product.brand_id || "";
    document.getElementById("p-compare").value = product.compare_at_price || "";
    document.getElementById("p-description").value = product.description || "";
    document.getElementById("p-image").value = product.image_url || "";
    document.getElementById("p-short").value = product.short_description || "";
    document.getElementById("p-published").checked = Boolean(product.is_published);
    document.getElementById("p-featured").checked = Boolean(product.is_featured);
  },

  clearForm() {
    document.getElementById("product-form")?.reset();
    document.getElementById("product-edit-id").value = "";
    document.getElementById("form-title").textContent = OrionI18n.t('إضافة منتج', 'Add product');
    document.getElementById("p-quantity").value = "0";
  },

  payload() {
    return {
      name: document.getElementById("p-name").value.trim(),
      slug: document.getElementById("p-slug").value.trim(),
      price: document.getElementById("p-price").value,
      quantity: parseInt(document.getElementById("p-quantity").value || "0", 10),
      sku: document.getElementById("p-sku").value.trim() || null,
      category_id: document.getElementById("p-category").value || null,
      brand_id: document.getElementById("p-brand").value || null,
      compare_at_price: document.getElementById("p-compare").value || null,
      description: document.getElementById("p-description").value.trim() || null,
      image_url: document.getElementById("p-image").value.trim() || null,
      short_description: document.getElementById("p-short").value.trim() || null,
      is_published: document.getElementById("p-published").checked,
      is_featured: document.getElementById("p-featured").checked,
    };
  },

  init() {
    const form = document.getElementById("product-form");
    if (!form) return;
    this.loadCategories();
    this.loadBrands();
    this.loadProducts();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const msg = document.getElementById("product-msg");
      const editId = document.getElementById("product-edit-id").value;
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
