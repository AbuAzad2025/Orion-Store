/** Storefront API client — /api/v1/store/* (wave 5 #55). */
const StoreAPI = {
  tenantId: document.body.dataset.tenantId || "",
  cartTokenKey: "orion_cart_token",
  headers() {
    return {
      "Content-Type": "application/json",
      "X-Tenant-ID": this.tenantId,
      "X-Locale": document.documentElement.lang || "ar",
    };
  },
  async request(method, path, body) {
    const opts = { method, headers: this.headers() };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(`/api/v1/store${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  },
  listProducts() {
    return this.request("GET", "/products");
  },
  getProduct(slug) {
    return this.request("GET", `/products/${slug}`);
  },
  createCart() {
    return this.request("POST", "/cart");
  },
  getCart(token) {
    return this.request("GET", `/cart/${token}`);
  },
  addItem(token, productId, quantity) {
    return this.request("POST", `/cart/${token}/items`, {
      product_id: productId,
      quantity: quantity || 1,
    });
  },
  addBundle(token, bundleId, quantity) {
    return this.request("POST", `/cart/${token}/bundle`, {
      bundle_id: bundleId,
      quantity: quantity || 1,
    });
  },
  whatsappMessage(token, payload) {
    return this.request("POST", `/cart/${token}/whatsapp-message`, payload || {});
  },
  whatsappOrder(token, payload) {
    return this.request("POST", `/cart/${token}/whatsapp-order`, payload || {});
  },
  productWhatsappOrder(productId, payload) {
    return this.request("POST", `/product/${productId}/whatsapp-order`, payload || {});
  },
  checkout(cartToken, customerEmail, shippingAddress, extras) {
    const body = {
      cart_token: cartToken,
      customer_email: customerEmail,
      shipping_address: shippingAddress || {},
    };
    if (extras) {
      if (extras.shipping_method_code) {
        body.shipping_method_code = extras.shipping_method_code;
      }
      if (extras.voucher_code) body.voucher_code = extras.voucher_code;
      if (extras.idempotency_key) body.idempotency_key = extras.idempotency_key;
      if (extras.use_store_credit) body.use_store_credit = true;
      if (extras.pickup_location_id) body.pickup_location_id = extras.pickup_location_id;
    }
    return this.request("POST", "/checkout", body);
  },
  listShippingMethods() {
    return this.request("GET", "/shipping/methods");
  },
  listPaymentMethods() {
    return this.request("GET", "/payment-methods");
  },
  validateVoucher(code, subtotal) {
    return fetch(
      `/api/v1/vouchers/${encodeURIComponent(code)}/validate?subtotal=${subtotal}`,
      { headers: this.headers() }
    )
      .then((res) => res.json().then((data) => {
        if (!res.ok) throw new Error(data.error || res.statusText);
        return data;
      }));
  },
  payOrder(publicId, paymentMethod) {
    return this.request("POST", `/orders/${publicId}/pay`, {
      payment_method: paymentMethod || "cod",
    });
  },
  getOrder(publicId) {
    return this.request("GET", `/orders/${publicId}`);
  },
  async subscribeStockNotification(productId, customerEmail) {
    const res = await fetch("/api/v1/stock-notifications", {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ product_id: productId, customer_email: customerEmail }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  },

  getCartToken() {
    return localStorage.getItem(this.cartTokenKey);
  },
  setCartToken(token) {
    localStorage.setItem(this.cartTokenKey, token);
  },
};
