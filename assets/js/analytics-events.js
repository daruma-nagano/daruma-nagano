// GA4-ready event scaffold. Add GA4 later; this file works without a measurement ID.
(function () {
  function pageLanguage() {
    return document.documentElement.lang && document.documentElement.lang.startsWith("en") ? "en" : "ja";
  }
  function pageType() {
    const path = location.pathname;
    if (path.includes("/purchase/box/")) return "purchase_box";
    if (path.includes("/purchase/psa/")) return "purchase_psa";
    if (path.includes("/purchase/single/")) return "purchase_single";
    if (path.includes("/purchase/")) return "purchase";
    if (path.includes("/company/")) return "company";
    if (path.includes("/en/")) return "en_top";
    if (path.includes("/ja/")) return "ja_top";
    return "root";
  }
  window.trackDarumaEvent = function (eventName, params) {
    const payload = Object.assign({ page_language: pageLanguage(), page_type: pageType(), page_path: location.pathname }, params || {});
    if (typeof window.gtag === "function") window.gtag("event", eventName, payload);
    if (localStorage.getItem("darumaDebugEvents") === "1") console.log("[DarumaEvent]", eventName, payload);
  };
  document.addEventListener("click", function (event) {
    const link = event.target.closest("a");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    const label = (link.textContent || "").trim();
    if (href.startsWith("tel:")) return window.trackDarumaEvent("click_phone", { link_text: label });
    if (href.includes("maps.app.goo.gl") || href.includes("google.com/maps")) return window.trackDarumaEvent("click_google_map", { link_text: label });
    if (href.includes("instagram.com")) return window.trackDarumaEvent("click_instagram", { link_text: label });
    if (href.includes("threads.com")) return window.trackDarumaEvent("click_threads", { link_text: label });
    if (href.includes("x.com") || href.includes("twitter.com")) return window.trackDarumaEvent("click_x", { link_text: label });
    if (href.includes("line.me") || href.includes("lin.ee")) return window.trackDarumaEvent("click_line", { link_text: label });
    if (href.includes("/en/") || href.includes("/ja/")) return window.trackDarumaEvent("click_internal_navigation", { link_text: label, href: href });
  });
})();
