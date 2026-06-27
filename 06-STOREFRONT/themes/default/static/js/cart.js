/** Cart page interactions (wave 5 #56). */
document.addEventListener("DOMContentLoaded", async () => {
  const listEl = document.getElementById("cart-items");
  const summaryEl = document.getElementById("cart-summary");
  if (!listEl) return;

  let token = StoreAPI.getCartToken();
  if (!token) {
    const created = await StoreAPI.createCart();
    token = created.cart.cart_token;
    StoreAPI.setCartToken(token);
  }

  async function refresh() {
    const data = await StoreAPI.getCart(token);
    if (!data.items.length) {
      listEl.innerHTML = "<p class='text-gray-500'>السلة فارغة.</p>";
      summaryEl.textContent = "";
      return;
    }
    listEl.innerHTML = data.items
      .map(
        (i) =>
          `<div class="flex justify-between border-b py-2"><span>${i.product_name || i.product_id}</span><span>${i.quantity} × ${i.unit_price}</span></div>`
      )
      .join("");
    summaryEl.innerHTML = `<a href="/checkout" class="inline-block mt-4 rounded bg-emerald-600 px-4 py-2 text-white">إتمام الشراء</a>`;
  }

  refresh().catch((err) => {
    listEl.textContent = err.message;
  });

  document.querySelectorAll("[data-add-cart]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const productId = parseInt(btn.dataset.addCart, 10);
      await StoreAPI.addItem(token, productId, 1);
      await refresh();
    });
  });
});
