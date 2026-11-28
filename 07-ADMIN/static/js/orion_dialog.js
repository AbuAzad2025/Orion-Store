/** Shared accessible-dialog focus trap (storefront + admin). */
(function (global) {
  "use strict";
  if (global.OrionDialog) return;

  var FOCUSABLE = [
    "a[href]", "area[href]", "button:not([disabled])",
    "input:not([disabled]):not([type=hidden])",
    "select:not([disabled])", "textarea:not([disabled])",
    "[contenteditable]", "[tabindex]:not([tabindex='-1'])"
  ].join(",");

  var active = new WeakMap();

  function items(dialog) {
    return Array.prototype.filter.call(
      dialog.querySelectorAll(FOCUSABLE),
      function (el) {
        if (el.hasAttribute("disabled") || el.getAttribute("aria-hidden") === "true") {
          return false;
        }
        return el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement;
      }
    );
  }

  function trap(dialog, options) {
    if (!dialog || active.has(dialog)) return;
    var opts = options || {};
    var state = {
      returnTo: document.activeElement,
      addedTabindex: false,
      onKeydown: null
    };
    if (!dialog.hasAttribute("role")) dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    if (!dialog.hasAttribute("tabindex")) {
      dialog.setAttribute("tabindex", "-1");
      state.addedTabindex = true;
    }

    state.onKeydown = function (event) {
      if (event.key === "Escape") {
        if (typeof opts.onEscape === "function") {
          event.preventDefault();
          opts.onEscape();
        }
        return;
      }
      if (event.key !== "Tab") return;
      var list = items(dialog);
      if (!list.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      var first = list[0];
      var last = list[list.length - 1];
      var current = document.activeElement;
      if (event.shiftKey &&
          (current === first || current === dialog || !dialog.contains(current))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (current === last || !dialog.contains(current))) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", state.onKeydown, true);
    active.set(dialog, state);
    var initial = opts.initialFocus ? dialog.querySelector(opts.initialFocus) : null;
    (initial || items(dialog)[0] || dialog).focus();
  }

  function release(dialog) {
    if (!dialog) return;
    var state = active.get(dialog);
    if (!state) return;
    document.removeEventListener("keydown", state.onKeydown, true);
    active.delete(dialog);
    if (state.addedTabindex) dialog.removeAttribute("tabindex");
    if (state.returnTo && typeof state.returnTo.focus === "function") {
      state.returnTo.focus();
    }
  }

  global.OrionDialog = { trap: trap, release: release };
})(window);
