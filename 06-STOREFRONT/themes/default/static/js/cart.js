/** Cart page interactions (wave 5 #56) — lazy cart init. */
document.addEventListener("DOMContentLoaded", async () => {
  const listEl = document.getElementById("cart-items");
  const waBtn = document.getElementById("whatsapp-order-btn");
  const waMsg = document.getElementById("wa-msg");

  const isArabic = document.documentElement.lang === "ar";
  const tr = (ar, en) => (isArabic ? ar : en);
  const currency = document.body.dataset.currency || "ILS";
  const sourceCurrency = document.body.dataset.sourceCurrency || currency;
  const fxRate = parseFloat(document.body.dataset.fxRate || "0") || 0;
  const convert = (value) =>
    currency !== sourceCurrency && fxRate ? value * fxRate : value;
  const money = (value) => convert(parseFloat(value || 0) || 0).toFixed(2);
  const emptyText = listEl?.dataset.empty || tr("السلة فارغة.", "The cart is empty.");
  const totalLabel = document.getElementById("cart-total")?.dataset.total || tr("المجموع:", "Total:");

  async function ensureCart() {
    let token = StoreAPI.getCartToken();
    if (!token) {
      const created = await StoreAPI.createCart();
      token = created.cart.cart_token;
      StoreAPI.setCartToken(token);
    }
    return token;
  }

  function showEmpty() {
    if (listEl) {
      SafeDOM.clear(listEl);
      listEl.appendChild(SafeDOM.elem("p", { className: "text-gray-500" }, [emptyText]));
    }
    if (waBtn) waBtn.disabled = true;
    const totalEl = document.getElementById("cart-total");
    if (totalEl) totalEl.textContent = "";
  }

  async function refresh() {
    const token = StoreAPI.getCartToken();
    if (!token) { showEmpty(); return; }
    const data = await StoreAPI.getCart(token);
    if (!data.items.length) { showEmpty(); return; }
    if (waBtn) waBtn.disabled = false;
    if (listEl) {
      SafeDOM.clear(listEl);
      let total = 0;
      data.items.forEach((i) => {
        const line = parseFloat(i.total_price || 0) || 0;
        total += line;
        listEl.appendChild(SafeDOM.elem("div", { className: "flex justify-between border-b py-2" }, [
          SafeDOM.elem("span", {}, [i.product_name || i.product_id]),
          SafeDOM.elem("span", {}, [`${i.quantity} × ${money(i.unit_price)} ${currency}`]),
        ]));
      });
      const totalEl = document.getElementById("cart-total");
      if (totalEl) totalEl.textContent = `${totalLabel} ${money(total)} ${currency}`;
    }
  }

  waBtn?.addEventListener("click", async () => {
    const token = StoreAPI.getCartToken();
    if (!token) {
      if (waMsg) waMsg.textContent = emptyText;
      return;
    }
    waBtn.disabled = true;
    try {
      const result = await StoreAPI.whatsappOrder(token, {
        customer_name: document.getElementById("wa-customer-name")?.value || "",
        notes: document.getElementById("wa-notes")?.value || "",
      });
      if (!result.url) throw new Error(tr("رقم واتساب غير مُضبط لهذا المتجر.", "No WhatsApp number is configured for this store."));
      window.open(result.url, "_blank", "noopener,noreferrer");
      if (waMsg) waMsg.textContent = tr("تم تسجيل الطلب — أكمل الإرسال في واتساب وسيتم تأكيده من المتجر.", "Order recorded — finish sending in WhatsApp; the store will confirm it.");
    } catch (err) {
      if (waMsg) waMsg.textContent = err.message;
    } finally {
      waBtn.disabled = false;
    }
  });

  if (listEl) {
    refresh().catch((err) => {
      listEl.textContent = err.message;
    });
  }

  document.querySelectorAll("[data-add-cart]").forEach((btn) => {
    const originalText = btn.textContent;
    btn.addEventListener("click", async () => {
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = tr("جارٍ الإضافة…", "Adding…");
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
