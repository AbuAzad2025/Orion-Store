/** One-click store sharing: native sheet on mobile, full social menu elsewhere. */
(function () {
  function setLinks(panel, url, title) {
    const e = encodeURIComponent;
    const text = title + " — " + url;
    const targets = {
      whatsapp: "https://wa.me/?text=" + e(text),
      facebook: "https://www.facebook.com/sharer/sharer.php?u=" + e(url),
      x: "https://twitter.com/intent/tweet?text=" + e(title) + "&url=" + e(url),
      telegram: "https://t.me/share/url?url=" + e(url) + "&text=" + e(title),
      linkedin: "https://www.linkedin.com/sharing/share-offsite/?url=" + e(url),
      email: "mailto:?subject=" + e(title) + "&body=" + e(text),
    };
    panel.querySelectorAll("[data-share-target]").forEach(function (a) {
      const href = targets[a.dataset.shareTarget];
      if (href) a.setAttribute("href", href);
    });
    const copy = panel.querySelector("[data-store-copy]");
    if (copy) copy.dataset.storeCopy = url;
  }
  function close(panel) {
    if (typeof OrionDialog !== "undefined") OrionDialog.release(panel);
    panel.classList.add("hidden");
    panel.classList.remove("flex");
  }
  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-store-share]");
    if (trigger) {
      event.preventDefault();
      const url = trigger.dataset.shareUrl || location.origin + location.pathname;
      const title = trigger.dataset.shareTitle || document.title;
      const panel = document.querySelector("[data-store-share-panel]");
      if (navigator.share) {
        navigator.share({ title: title, text: title, url: url }).catch(function (err) {
          if (err && err.name === "AbortError") return;
          if (panel) { setLinks(panel, url, title); panel.classList.remove("hidden"); panel.classList.add("flex");
          if (typeof OrionDialog !== "undefined") {
            OrionDialog.trap(panel, { onEscape: function () { close(panel); } });
          }
        }
        });
        return;
      }
      if (panel) { setLinks(panel, url, title); panel.classList.remove("hidden"); panel.classList.add("flex");
          if (typeof OrionDialog !== "undefined") {
            OrionDialog.trap(panel, { onEscape: function () { close(panel); } });
          }
        }
      return;
    }
    if (event.target.closest("[data-store-share-close]")) {
      const p = document.querySelector("[data-store-share-panel]");
      if (p) close(p);
      return;
    }
    if (event.target.matches("[data-store-share-panel]")) {
      close(event.target);
      return;
    }
    const copy = event.target.closest("[data-store-copy]");
    if (copy) {
      event.preventDefault();
      const url = copy.dataset.storeCopy || "";
      const msg = document.querySelector("[data-store-share-msg]");
      function done(ok) { if (msg) msg.textContent = ok ? (copy.dataset.copiedText || "Link copied") : (copy.dataset.failedText || "Could not copy link"); }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(function(){done(true);},function(){done(false);});
      } else {
        const el = document.createElement("textarea");
        el.value = url; el.setAttribute("readonly", ""); el.style.position = "fixed"; el.style.opacity = "0";
        document.body.appendChild(el); el.select();
        let ok = false; try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
        el.remove(); done(ok);
      }
    }
  });
})();
