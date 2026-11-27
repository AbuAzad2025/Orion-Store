/** Safe DOM rendering for storefront — never uses innerHTML with untrusted data (AZ-0.11). */
const SafeDOM = {
  clear(el) { while (el.firstChild) el.removeChild(el.firstChild); },
  text(el, value) { el.textContent = value ?? ""; },
  elem(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);
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
};


// Currency switcher — moved out of an inline onchange handler for CSP strictness.
document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("currency-switch");
  if (!select) return;
  select.addEventListener("change", () => {
    const base = select.dataset.currencyBase || "";
    if (base && select.value) location.href = `${base}&currency=${encodeURIComponent(select.value)}`;
  });
});
