/** Checkout + pay flow (wave 5 #56, wave 6 shipping/voucher). */
document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("checkout-form");
  const resultEl = document.getElementById("checkout-result");
  const summaryEl = document.getElementById("checkout-summary");
  const methodSelect = document.getElementById("shipping-method");
  if (!form) return;

  let cartSubtotal = 0;
  try {
    const token = StoreAPI.getCartToken();
    if (token) {
      const cartData = await StoreAPI.getCart(token);
      cartSubtotal = (cartData.items || []).reduce(
        (sum, item) => sum + parseFloat(item.total_price || 0),
        0
      );
    }
    const methodsRes = await StoreAPI.listShippingMethods();
    methodSelect.innerHTML = "";
    (methodsRes.methods || []).forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.code;
      opt.textContent = `${m.name} — ${m.base_cost}`;
      methodSelect.appendChild(opt);
    });
    if (!methodsRes.methods || !methodsRes.methods.length) {
      methodSelect.innerHTML = '<option value="">لا توجد طرق شحن</option>';
    }
  } catch (err) {
    methodSelect.innerHTML = '<option value="">تعذر تحميل الشحن</option>';
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    resultEl.textContent = "جاري المعالجة...";
    try {
      const token = StoreAPI.getCartToken();
      if (!token) throw new Error("لا توجد سلة.");
      const email = document.getElementById("customer-email").value;
      const city = document.getElementById("shipping-city").value;
      const method = document.getElementById("payment-method").value;
      const shippingMethod = methodSelect.value || undefined;
      const voucherCode = document.getElementById("voucher-code").value.trim();
      const orderRes = await StoreAPI.checkout(token, email, { city }, {
        shipping_method_code: shippingMethod,
        voucher_code: voucherCode || undefined,
      });
      const order = orderRes.order;
      summaryEl.textContent = `المجموع: ${order.total} (شحن: ${order.shipping_cost})`;
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
