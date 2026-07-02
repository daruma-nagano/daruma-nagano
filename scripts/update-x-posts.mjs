import fs from "node:fs/promises";

const username = process.env.X_USERNAME || "kaitorinagano";
const rawBearer = process.env.X_BEARER_TOKEN || "";
const bearer = rawBearer.trim().replace(/^['\"]|['\"]$/g, "");
const output = "assets/data/x-posts.json";

async function writeFallback(message) {
  const fallback = {
    account: username,
    profileUrl: `https://x.com/${username}`,
    updatedAt: new Date().toISOString(),
    posts: [],
    note: message
  };
  await fs.mkdir("assets/data", { recursive: true });
  await fs.writeFile(output, JSON.stringify(fallback, null, 2), "utf8");
}

function isAscii(value) {
  return /^[\x00-\x7F]+$/.test(value);
}

if (!bearer) {
  await writeFallback("X_BEARER_TOKEN が未設定のため投稿取得をスキップしました。");
  console.log("X_BEARER_TOKEN is not set. Wrote fallback x-posts.json.");
  process.exit(0);
}

if (!isAscii(bearer) || bearer.includes("取得") || bearer.includes("Bearer Token")) {
  await writeFallback("X_BEARER_TOKEN が正しいBearer Tokenではないため投稿取得をスキップしました。");
  console.error("X_BEARER_TOKEN is invalid. Set the actual Bearer Token from X Developer Portal, not the Japanese placeholder text.");
  console.error("PowerShell example: $env:X_BEARER_TOKEN=\"AAAAAAAAAAAAAAAAAAAA...\"");
  process.exit(1);
}

const headers = { Authorization: `Bearer ${bearer}` };

try {
  const userRes = await fetch(`https://api.x.com/2/users/by/username/${username}`, { headers });
  if (!userRes.ok) throw new Error(`Failed to resolve X user: ${userRes.status} ${await userRes.text()}`);
  const userJson = await userRes.json();
  const userId = userJson?.data?.id;
  if (!userId) throw new Error("Failed to resolve X user ID.");

  const params = new URLSearchParams({
    max_results: "5",
    exclude: "retweets,replies",
    "tweet.fields": "created_at,public_metrics,entities"
  });

  const tweetsRes = await fetch(`https://api.x.com/2/users/${userId}/tweets?${params.toString()}`, { headers });
  if (!tweetsRes.ok) throw new Error(`Failed to fetch X posts: ${tweetsRes.status} ${await tweetsRes.text()}`);
  const tweetsJson = await tweetsRes.json();

  const posts = (tweetsJson.data || []).slice(0, 5).map((tweet) => ({
    id: tweet.id,
    text: tweet.text,
    createdAt: tweet.created_at,
    url: `https://x.com/${username}/status/${tweet.id}`,
    publicMetrics: tweet.public_metrics || {}
  }));

  const feed = {
    account: username,
    profileUrl: `https://x.com/${username}`,
    updatedAt: new Date().toISOString(),
    posts
  };

  await fs.mkdir("assets/data", { recursive: true });
  await fs.writeFile(output, JSON.stringify(feed, null, 2), "utf8");
  console.log(`Wrote ${posts.length} X posts to ${output}.`);
} catch (error) {
  await writeFallback(`X投稿の取得に失敗しました: ${error.message}`);
  console.error(error.message);
  process.exit(1);
}
