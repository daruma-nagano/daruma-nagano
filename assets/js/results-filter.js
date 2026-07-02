(function () {
  const list = document.querySelector("[data-results-list]");
  if (!list) return;
  const cards = Array.from(list.querySelectorAll("[data-result-card]"));
  const search = document.querySelector("[data-result-search]");
  const type = document.querySelector("[data-result-type]");
  function applyFilter() {
    const q = (search && search.value || "").trim().toLowerCase();
    const t = (type && type.value || "").trim();
    cards.forEach(function (card) {
      const text = card.textContent.toLowerCase();
      const matchQ = !q || text.includes(q);
      const matchT = !t || card.dataset.type === t;
      card.hidden = !(matchQ && matchT);
    });
  }
  if (search) search.addEventListener("input", applyFilter);
  if (type) type.addEventListener("change", applyFilter);
})();


/* SEARCH ALIAS FIX: OP13 / OP-13 / OP15 / OP-15 */
(function () {
  function normalizeSearchValue(value) {
    return String(value || "")
      .toUpperCase()
      .normalize("NFKC")
      .replace(/[‐‑‒–—―ー]/g, "-")
      .replace(/\s+/g, "")
      .trim();
  }

  function codeVariants(value) {
    const src = String(value || "").toUpperCase().normalize("NFKC");
    const variants = new Set([src, normalizeSearchValue(src)]);
    const re = /\b([A-Z]{2,4})[-\s]?(\d{1,3})\b/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      const pre = m[1];
      const num = m[2];
      variants.add(pre + num);
      variants.add(pre + "-" + num);
      variants.add(pre + " " + num);
      if (num.length === 2) {
        variants.add(pre + "0" + num);
        variants.add(pre + "-0" + num);
      }
    }
    return Array.from(variants);
  }

  window.darumaNormalizeSearch = normalizeSearchValue;
  window.darumaCodeVariants = codeVariants;

  function patchResultCards() {
    document.querySelectorAll("[data-result-card], .result-card, .purchase-result-card, [data-search]").forEach(function (card) {
      const base = [
        card.textContent || "",
        card.getAttribute("data-search") || "",
        card.getAttribute("data-code") || "",
        card.getAttribute("data-title") || ""
      ].join(" ");
      const merged = [base].concat(codeVariants(base)).join(" ");
      card.setAttribute("data-search", merged);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", patchResultCards);
  } else {
    patchResultCards();
  }
  setTimeout(patchResultCards, 300);
  setTimeout(patchResultCards, 1000);
})();
