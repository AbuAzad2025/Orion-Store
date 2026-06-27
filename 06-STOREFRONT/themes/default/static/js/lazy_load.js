/** Below-fold image lazy loading (phase 14 — §18). */
document.addEventListener("DOMContentLoaded", () => {
  const images = document.querySelectorAll("img[data-lazy-src]");
  if (!images.length) return;

  const load = (img) => {
    if (!img.dataset.lazySrc) return;
    img.src = img.dataset.lazySrc;
    img.removeAttribute("data-lazy-src");
  };

  if (!("IntersectionObserver" in window)) {
    images.forEach(load);
    return;
  }

  const observer = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        load(entry.target);
        obs.unobserve(entry.target);
      });
    },
    { rootMargin: "200px" }
  );

  images.forEach((img) => observer.observe(img));
});
