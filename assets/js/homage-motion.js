// Motion-heavy storefront layer for Daruma Kaitori Nagano.
// Inspired by modern TCG store landing-page behavior, not by copying another site.

(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;

  function qs(selector, scope) {
    return (scope || document).querySelector(selector);
  }

  function qsa(selector, scope) {
    return Array.from((scope || document).querySelectorAll(selector));
  }

  // Smooth anchor navigation.
  document.addEventListener("click", function (event) {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;

    const target = qs(link.getAttribute("href"));
    if (!target) return;

    event.preventDefault();
    target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  });

  // Scroll progress.
  const progress = qs("[data-scroll-progress]");
  function updateProgress() {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = max > 0 ? Math.min(1, Math.max(0, scrollTop / max)) : 0;
    root.style.setProperty("--scroll-ratio", ratio.toFixed(4));
    if (progress) progress.style.transform = "scaleX(" + ratio + ")";
  }

  // Active nav.
  const sections = qsa("[data-motion-section]");
  const navLinks = qsa("[data-motion-link]");
  if ("IntersectionObserver" in window && sections.length) {
    const activeObserver = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

      if (!visible) return;

      const id = visible.target.id;
      navLinks.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === "#" + id);
      });
    }, { rootMargin: "-30% 0px -58% 0px", threshold: [0.12, 0.28, 0.5, 0.72] });

    sections.forEach((section) => activeObserver.observe(section));
  }

  // Reveal sections.
  const revealItems = qsa("[data-motion-reveal]");
  if ("IntersectionObserver" in window && revealItems.length) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-motion-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.14, rootMargin: "0px 0px -8% 0px" });

    revealItems.forEach((item) => revealObserver.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-motion-visible"));
  }

  // Hero parallax.
  const hero = qs(".motion-hero");
  const parallaxItems = qsa("[data-parallax]");
  function updateParallax() {
    if (reduceMotion || !parallaxItems.length) return;
    const y = window.scrollY || 0;
    parallaxItems.forEach((item, index) => {
      const speed = Number(item.getAttribute("data-parallax")) || 0.05;
      const offset = Math.round(y * speed);
      item.style.transform = "translate3d(0, " + offset + "px, 0)";
    });
  }

  // Mouse tilt for hero cards.
  const tiltZone = qs("[data-tilt-zone]");
  if (!reduceMotion && tiltZone) {
    tiltZone.addEventListener("pointermove", function (event) {
      const rect = tiltZone.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      root.style.setProperty("--tilt-x", (x * 14).toFixed(2) + "deg");
      root.style.setProperty("--tilt-y", (y * -14).toFixed(2) + "deg");
    });

    tiltZone.addEventListener("pointerleave", function () {
      root.style.setProperty("--tilt-x", "0deg");
      root.style.setProperty("--tilt-y", "0deg");
    });
  }

  // Page top.
  const topButton = qs("[data-page-top]");
  if (topButton) {
    topButton.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  function onScroll() {
    updateProgress();
    updateParallax();

    if (topButton) {
      topButton.classList.toggle("is-visible", window.scrollY > 520);
    }
  }

  updateProgress();
  updateParallax();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", updateProgress);
})();
