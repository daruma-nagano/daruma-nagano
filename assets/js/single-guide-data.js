/* Single purchase guide data loader: gradual migration from inline HTML to JSON */
(function () {
  fetch("/daruma-nagano/assets/data/single-purchase-guide.json")
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !Array.isArray(data.items)) return;
      window.darumaSinglePurchaseGuideData = data.items;
      document.documentElement.setAttribute("data-single-guide-json", "loaded");
    })
    .catch(function () {});
})();
