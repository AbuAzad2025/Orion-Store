/** Safe DOM rendering — never uses innerHTML with untrusted data (AZ-0.11). */
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
  actionBtn(label, className, onClick) {
    const btn = this.elem("button", { className }, [label]);
    if (onClick) btn.addEventListener("click", onClick);
    return btn;
  },
};
