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
  checkout(cartToken, customerEmail, shippingAddress) {
    return this.request("POST", "/checkout", {
      cart_token: cartToken,
      customer_email: customerEmail,
      shipping_address: shippingAddress || {},
    });
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
