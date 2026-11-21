/** Safe DOM rendering — never uses innerHTML with untrusted data (AZ-0.11). */
const SafeDOM = {
  clear(el) { while (el.firstChild) el.removeChild(el.firstChild); },
  text(el, value) { el.textContent = value ?? ""; },
  elem(tag, attributes = {}, children = []) {
    const el = document.createElement(tag);
    const attrs = attributes || {};
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "className") el.className = v;
      else if (k === "textContent") el.textContent = v;
      else el.setAttribute(k, v);
    }
    for (const c of children) {
      if (typeof c === "string" || typeof c === "number") {
        el.appendChild(document.createTextNode(String(c)));
      } else if (c instanceof Node) {
        el.appendChild(c);
      }
    }
    return el;
  },
  emptyMsg(text) {
    return this.elem("p", { className: "text-gray-500" }, [text]);
  },
  actionBtn(label, className, onClick) {
    const btn = this.elem("button", { className }, [label]);
    if (onClick) btn.addEventListener("click", onClick);
    return btn;
  },
};

/** Shared UI feedback layer — toasts, danger confirmation, loading states. */
const OrionUI = {
  toast(message, kind = "info") {
    let host = document.querySelector(".orion-toast-host");
    if (!host) {
      host = SafeDOM.elem("div", { className: "orion-toast-host", role: "status", "aria-live": "polite" });
      document.body.appendChild(host);
    }
    const toast = SafeDOM.elem("div", { className: `orion-toast orion-toast-${kind}`, role: "alert" }, [message]);
    host.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
    return toast;
  },

  confirmDanger(message) {
    return window.confirm(message);
  },

  async withLoading(element, task) {
    if (!element) return task();
    element.setAttribute("aria-busy", "true");
    element.classList.add("orion-loading");
    try {
      return await task();
    } finally {
      element.removeAttribute("aria-busy");
      element.classList.remove("orion-loading");
    }
  },
};

document.addEventListener("orion-api-error", (event) => {
  const detail = event.detail || {};
  OrionUI.toast(detail.error?.message || "حدث خطأ غير متوقع", "error");
});
