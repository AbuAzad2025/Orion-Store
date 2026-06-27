/** Checkout + pay flow (wave 5 #56). */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("checkout-form");
  const resultEl = document.getElementById("checkout-result");
  if (!form) return;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    resultEl.textContent = "جاري المعالجة...";
    try {
      const token = StoreAPI.getCartToken();
      if (!token) throw new Error("لا توجد سلة.");
      const email = document.getElementById("customer-email").value;
      const city = document.getElementById("shipping-city").value;
      const method = document.getElementById("payment-method").value;
      const orderRes = await StoreAPI.checkout(token, email, { city });
      const order = orderRes.order;
      const payRes = await StoreAPI.payOrder(order.public_id, method);
      resultEl.innerHTML = `<p class="text-green-700">تم الدفع — رقم الطلب ${order.order_number}</p>`;
      if (payRes.invoice) {
        resultEl.innerHTML += `<p class="text-sm">فاتورة: ${payRes.invoice.invoice_number}</p>`;
      }
      localStorage.removeItem(StoreAPI.cartTokenKey);
    } catch (err) {
      resultEl.textContent = err.message;
    }
  });
});
