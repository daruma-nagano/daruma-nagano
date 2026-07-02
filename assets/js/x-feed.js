(() => {
  const X_URL = "https://x.com/kaitorinagano";
  const INSTAGRAM_URL = "https://www.instagram.com/darumakaitori.nagano";
  const THREADS_URL = "https://www.threads.com/@darumakaitori.nagano";

  const isEnglishPage = () => {
    const lang = (document.documentElement.lang || "").toLowerCase();
    const path = window.location.pathname || "";
    return lang.startsWith("en") || path.includes("/en/");
  };

  const labels = () => {
    if (isEnglishPage()) {
      return {
        label: "SNS Updates",
        title: "Follow us for the latest updates",
        body: "Buying prices, new arrivals and business updates are posted on X, Instagram and Threads.",
        x: "View X",
        instagram: "View Instagram",
        threads: "View Threads"
      };
    }

    return {
      label: "SNS 最新情報",
      title: "最新情報は各SNSで更新しています",
      body: "買取価格・入荷情報・営業情報は、X・Instagram・Threadsをご確認ください。",
      x: "Xを見る",
      instagram: "Instagramを見る",
      threads: "Threadsを見る"
    };
  };

  const renderSnsOnly = (container) => {
    const t = labels();
    container.innerHTML = `
      <div class="sns-only-card">
        <p class="sns-only-label">${t.label}</p>
        <h3>${t.title}</h3>
        <p>${t.body}</p>
        <div class="sns-actions">
          <a class="btn secondary" href="${X_URL}" target="_blank" rel="noopener">${t.x}</a>
          <a class="btn ghost" href="${INSTAGRAM_URL}" target="_blank" rel="noopener">${t.instagram}</a>
          <a class="btn ghost" href="${THREADS_URL}" target="_blank" rel="noopener">${t.threads}</a>
        </div>
      </div>
    `;
  };

  const mount = () => {
    document.querySelectorAll("[data-x-feed]").forEach(renderSnsOnly);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
