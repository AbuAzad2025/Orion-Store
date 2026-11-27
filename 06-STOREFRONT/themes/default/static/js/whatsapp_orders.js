/** Register a pending WhatsApp order before opening the chat. */
(function () {
  document.addEventListener("click", async function (event) {
    const link = event.target.closest("[data-wa-product]");
    if (!link) return;
    event.preventDefault();
    try {
      const result = await StoreAPI.productWhatsappOrder(link.dataset.waProduct, {
        quantity: Number(link.dataset.waQty || 1),
      });
      if (result.url) window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      window.open(link.href, "_blank", "noopener,noreferrer");
    }
  });
})();
