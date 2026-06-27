/** Storefront API client — /api/v1/store/* (wave 5 #55). */
const StoreAPI = {
  tenantId: document.body.dataset.tenantId || "",
  cartTokenKey: "orion_cart_token",
  headers() {
    return {
      "Content-Type": "application/json",
      "X-Tenant-ID": this.tenantId,
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
    }
    return this.request("POST", "/checkout", body);
  },
  listShippingMethods() {
    return this.request("GET", "/shipping/methods");
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
  getCartToken() {
    return localStorage.getItem(this.cartTokenKey);
  },
  setCartToken(token) {
    localStorage.setItem(this.cartTokenKey, token);
  },
};
