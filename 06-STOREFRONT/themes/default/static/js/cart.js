/** Cart page interactions (wave 5 #56) — lazy cart init. */
document.addEventListener("DOMContentLoaded", async () => {
  const listEl = document.getElementById("cart-items");
  const summaryEl = document.getElementById("cart-summary");

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
      if (listEl) listEl.innerHTML = "<p class='text-gray-500'>السلة فارغة.</p>";
      if (summaryEl) summaryEl.textContent = "";
      return;
    }
    const data = await StoreAPI.getCart(token);
    if (!data.items.length) {
      if (listEl) listEl.innerHTML = "<p class='text-gray-500'>السلة فارغة.</p>";
      if (summaryEl) summaryEl.textContent = "";
      return;
    }
    if (listEl) {
      listEl.innerHTML = data.items
        .map(
          (i) =>
            `<div class="flex justify-between border-b py-2"><span>${i.product_name || i.product_id}</span><span>${i.quantity} × ${i.unit_price}</span></div>`
        )
        .join("");
    }
    if (summaryEl) {
      summaryEl.innerHTML = `<a href="/checkout" class="inline-block mt-4 rounded bg-emerald-600 px-4 py-2 text-white">إتمام الشراء</a>`;
    }
  }

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
