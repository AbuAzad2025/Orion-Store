/** Storefront UI polish: compact header on scroll without inline handlers. */
(function () {
  function sync() {
    document.body.classList.toggle("is-scrolled", window.scrollY > 40);
  }
  if (window.addEventListener) {
    window.addEventListener("scroll", sync, { passive: true });
    sync();
  }
})();
