/** Product sharing — WhatsApp + copy link, no inline handlers (CSP-safe). */
(function () {
  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    const input = document.createElement("textarea");
    input.value = text;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    const ok = document.execCommand("copy");
    input.remove();
    return ok ? Promise.resolve() : Promise.reject(new Error("copy failed"));
  }
  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-copy-share]");
    if (!button) return;
    event.preventDefault();
    const url = button.dataset.copyShare || "";
    const msg = document.querySelector("[data-share-msg]");
    const okText = button.dataset.copiedText || "Link copied";
    const failText = button.dataset.failedText || "Could not copy link";
    copy(url).then(
      function () { if (msg) msg.textContent = okText; },
      function () { if (msg) msg.textContent = failText; }
    );
  });
})();
