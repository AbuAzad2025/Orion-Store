/** Checkout + pay flow (wave 5 #56, wave 6 shipping/voucher). */
const isArabic = document.documentElement.lang === "ar";
const tr = (ar, en) => (isArabic ? ar : en);
document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("checkout-form");
  const resultEl = document.getElementById("checkout-result");
  const summaryEl = document.getElementById("checkout-summary");
  const methodSelect = document.getElementById("shipping-method");
  const paymentSelect = document.getElementById("payment-method");
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
    const [methodsRes, payRes, pickupRes] = await Promise.all([
      StoreAPI.listShippingMethods(),
      StoreAPI.listPaymentMethods(),
      StoreAPI.request("GET", "/pickup-locations").catch(() => ({ locations: [] })),
    ]);
    const pickupSelect = document.getElementById("pickup-location");
    const pickupRow = document.getElementById("pickup-row");
    if (pickupSelect && pickupRow && (pickupRes.locations || []).length) {
      for (const loc of pickupRes.locations) {
        pickupSelect.appendChild(
          SafeDOM.elem("option", { value: loc.id }, [`${loc.name} — ${loc.code}`])
        );
      }
      pickupRow.classList.remove("hidden");
    }
    SafeDOM.clear(methodSelect);
    (methodsRes.methods || []).forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.code;
      opt.textContent = `${m.name} — ${m.base_cost}`;
      methodSelect.appendChild(opt);
    });
    if (!methodsRes.methods || !methodsRes.methods.length) {
      SafeDOM.clear(methodSelect);
      methodSelect.appendChild(SafeDOM.elem("option", { value: "" }, [tr("لا توجد طرق شحن", "No shipping methods available.")]));
    }
    if (paymentSelect) {
      SafeDOM.clear(paymentSelect);
      const notes = document.getElementById("payment-instructions");
      const instructionsByCode = {};
      (payRes.payment_methods || []).forEach((pm) => {
        const opt = document.createElement("option");
        opt.value = pm.code;
        opt.textContent = pm.label;
        paymentSelect.appendChild(opt);
        if (pm.instructions) instructionsByCode[pm.code] = pm.instructions;
      });
      if (!payRes.payment_methods || !payRes.payment_methods.length) {
        SafeDOM.clear(paymentSelect);
        paymentSelect.appendChild(SafeDOM.elem("option", { value: "cod" }, [tr("الدفع عند الاستلام", "Cash on delivery")]));
      }
      if (notes) {
        const showNotes = () => {
          const text = instructionsByCode[paymentSelect.value] || "";
          notes.textContent = text;
          notes.classList.toggle("hidden", !text);
        };
        paymentSelect.addEventListener("change", showNotes);
        showNotes();
      }
    }
  } catch (err) {
    SafeDOM.clear(methodSelect);
    methodSelect.appendChild(SafeDOM.elem("option", { value: "" }, [tr("تعذر تحميل الشحن", "Could not load shipping options.")]));
    if (paymentSelect) {
      SafeDOM.clear(paymentSelect);
      paymentSelect.appendChild(SafeDOM.elem("option", { value: "cod" }, [tr("الدفع عند الاستلام", "Cash on delivery")]));
    }
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (form.dataset.busy) return;
    form.dataset.busy = "1";
    resultEl.textContent = tr("جاري المعالجة...", "Processing...");
    try {
      const token = StoreAPI.getCartToken();
      if (!token) throw new Error(tr("لا توجد سلة.", "No cart is available."));
      const email = document.getElementById("customer-email").value;
      const city = document.getElementById("shipping-city").value;
      const countryCode = document.getElementById("shipping-country")?.value.trim() || "";
      const region = document.getElementById("shipping-region")?.value.trim() || "";
      const method = document.getElementById("payment-method").value;
      const shippingMethod = methodSelect.value || undefined;
      const voucherCode = document.getElementById("voucher-code").value.trim();
      const idempotencyKey = crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const shippingAddress = {
        city,
        country_code: countryCode || undefined,
        region: region || undefined,
      };
      const orderRes = await StoreAPI.checkout(token, email, shippingAddress, {
        shipping_method_code: shippingMethod,
        voucher_code: voucherCode || undefined,
        idempotency_key: idempotencyKey,
        use_store_credit: document.getElementById("use-store-credit")?.checked || false,
        pickup_location_id: document.getElementById("pickup-location")?.value || undefined,
      });
      const order = orderRes.order;
      summaryEl.textContent = `${tr("المجموع:", "Total:")} ${order.total} ${tr("(شحن:", "(Shipping:")} ${order.shipping_cost})`;
      const payRes = await StoreAPI.payOrder(order.public_id, method);
      SafeDOM.clear(resultEl);
      resultEl.appendChild(SafeDOM.elem("p", { className: "text-green-700" }, [`${tr("تم الدفع", "Payment successful")} — ${tr("رقم الطلب", "Order #")}${order.order_number}`]));
      if (payRes.invoice) {
        resultEl.appendChild(SafeDOM.elem("p", { className: "text-sm" }, [
          `${tr("فاتورة:", "Invoice:")} ${payRes.invoice.invoice_number} `,
          SafeDOM.elem("a", {
            href: `/api/v1/store/orders/${order.public_id}/invoice.pdf`,
            className: "orion-header-link underline",
            target: "_blank",
            rel: "noopener",
          }, [tr("تحميل PDF", "Download PDF")])
        ]));
      }
      localStorage.removeItem(StoreAPI.cartTokenKey);
    } catch (err) {
      resultEl.textContent = err.message;
    } finally {
      delete form.dataset.busy;
    }
  });
});
