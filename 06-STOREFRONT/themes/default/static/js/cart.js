/** Cart page interactions (wave 5 #56) — lazy cart init. */
document.addEventListener("DOMContentLoaded", async () => {
  const listEl = document.getElementById("cart-items");
  const waBtn = document.getElementById("whatsapp-order-btn");
  const waMsg = document.getElementById("wa-msg");

  async function ensureCart() {
    let token = StoreAPI.getCartToken();
    if (!token) {
      const created = await StoreAPI.createCart();
      token = created.cart.cart_token;
      StoreAPI.setCartToken(token);
    }
    return token;
  }

  async function refresh() {
    const token = StoreAPI.getCartToken();
    if (!token) {
      if (listEl) { SafeDOM.clear(listEl); listEl.appendChild(SafeDOM.elem("p", { className: "text-gray-500" }, ["السلة فارغة."])); }
      if (waBtn) waBtn.disabled = true;
      const totalEl = document.getElementById("cart-total");
      if (totalEl) totalEl.textContent = "";
      return;
    }
    const data = await StoreAPI.getCart(token);
    if (!data.items.length) {
      if (listEl) { SafeDOM.clear(listEl); listEl.appendChild(SafeDOM.elem("p", { className: "text-gray-500" }, ["السلة فارغة."])); }
      if (waBtn) waBtn.disabled = true;
      const totalEl = document.getElementById("cart-total");
      if (totalEl) totalEl.textContent = "";
      return;
    }
    if (waBtn) waBtn.disabled = false;
    if (listEl) {
      SafeDOM.clear(listEl);
      const currency = document.body.dataset.currency || "ILS";
      let total = 0;
      data.items.forEach((i) => {
        const line = parseFloat(i.total_price || 0) || 0;
        total += line;
        listEl.appendChild(SafeDOM.elem("div", { className: "flex justify-between border-b py-2" }, [
          SafeDOM.elem("span", {}, [i.product_name || i.product_id]),
          SafeDOM.elem("span", {}, [`${i.quantity} × ${i.unit_price} ${currency}`]),
        ]));
      });
      const totalEl = document.getElementById("cart-total");
      if (totalEl) totalEl.textContent = `المجموع: ${total.toFixed(2)} ${currency}`;
    }
  }

  waBtn?.addEventListener("click", async () => {
    const token = StoreAPI.getCartToken();
    if (!token) {
      if (waMsg) waMsg.textContent = "السلة فارغة.";
      return;
    }
    waBtn.disabled = true;
    try {
      const result = await StoreAPI.whatsappMessage(token, {
        customer_name: document.getElementById("wa-customer-name")?.value || "",
        notes: document.getElementById("wa-notes")?.value || "",
      });
      if (!result.url) throw new Error("رقم واتساب غير مُضبط لهذا المتجر.");
      window.open(result.url, "_blank", "noopener,noreferrer");
      if (waMsg) waMsg.textContent = "تم تجهيز الطلب — أكمل الإرسال في واتساب.";
    } catch (err) {
      if (waMsg) waMsg.textContent = err.message;
    } finally {
      waBtn.disabled = false;
    }
  });

  // On cart page: load existing cart or show empty
  if (listEl) {
    refresh().catch((err) => {
      listEl.textContent = err.message;
    });
  }

  // Add-to-cart buttons — create cart lazily on first click
  document.querySelectorAll("[data-add-cart]").forEach((btn) => {
    const originalText = btn.textContent;
    btn.addEventListener("click", async () => {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = "...جاري";
      btn.classList.add("opacity-60", "cursor-wait");
      try {
        const productId = parseInt(btn.dataset.addCart, 10);
        const token = await ensureCart();
        await StoreAPI.addItem(token, productId, 1);
        if (listEl) await refresh();
      } finally {
        btn.disabled = false;
        btn.textContent = originalText;
        btn.classList.remove("opacity-60", "cursor-wait");
      }
    });
  });
});
