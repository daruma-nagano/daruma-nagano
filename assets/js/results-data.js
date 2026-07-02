/* Results data loader: gradual migration from inline HTML to JSON */
(function () {
  fetch("/daruma-nagano/assets/data/purchase-results-page.json")
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !Array.isArray(data.items)) return;
      window.darumaPurchaseResultsData = data.items;
      document.documentElement.setAttribute("data-results-json", "loaded");
    })
    .catch(function () {});
})();
