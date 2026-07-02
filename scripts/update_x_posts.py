"""
X投稿取得・画像自社保存スクリプト

目的:
- @kaitorinagano の公開投稿から最新5件を取得する
- 投稿に画像がある場合、先頭1枚だけ assets/img/x-posts/ に保存する
- assets/data/x-posts.json を画像対応形式で更新する

必要:
- Python 3.10+
- requests
- 環境変数 X_BEARER_TOKEN

実行:
  pip install requests
  $env:X_BEARER_TOKEN="xxxxx"
  python scripts/update_x_posts.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

USERNAME = "kaitorinagano"
MAX_RESULTS = 5
BASE_URL = "https://api.x.com/2"
OUTPUT_JSON = Path("assets/data/x-posts.json")
IMAGE_DIR = Path("assets/img/x-posts")
PUBLIC_IMAGE_BASE = "/daruma-nagano/assets/img/x-posts"


@dataclass
class XMedia:
    media_key: str
    type: str
    url: str | None = None
    preview_image_url: str | None = None


def require_token() -> str:
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token:
        raise RuntimeError("環境変数 X_BEARER_TOKEN が未設定です。")
    return token


def get_json(url: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def download_file(url: str, path: Path) -> None:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)


def get_user_id(token: str) -> str:
    data = get_json(f"{BASE_URL}/users/by/username/{USERNAME}", token)
    return data["data"]["id"]


def fetch_posts(token: str, user_id: str) -> dict[str, Any]:
    return get_json(
        f"{BASE_URL}/users/{user_id}/tweets",
        token,
        params={
            "max_results": MAX_RESULTS,
            "exclude": "replies,retweets",
            "tweet.fields": "created_at,attachments",
            "expansions": "attachments.media_keys",
            "media.fields": "url,preview_image_url,type",
        },
    )


def media_map(payload: dict[str, Any]) -> dict[str, XMedia]:
    result = {}
    for item in payload.get("includes", {}).get("media", []):
        media = XMedia(
            media_key=item.get("media_key", ""),
            type=item.get("type", ""),
            url=item.get("url"),
            preview_image_url=item.get("preview_image_url"),
        )
        if media.media_key:
            result[media.media_key] = media
    return result


def pick_first_image(tweet: dict[str, Any], media_by_key: dict[str, XMedia]) -> XMedia | None:
    keys = tweet.get("attachments", {}).get("media_keys", [])
    for key in keys:
        media = media_by_key.get(key)
        if not media:
            continue
        if media.type == "photo" and media.url:
            return media
        if media.type in {"video", "animated_gif"} and media.preview_image_url:
            return media
    return None


def extension_from_url(url: str) -> str:
    clean = url.split("?")[0].lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        if clean.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def build_output(payload: dict[str, Any]) -> dict[str, Any]:
    media_by_key = media_map(payload)
    posts = []

    for tweet in payload.get("data", [])[:MAX_RESULTS]:
        tweet_id = tweet["id"]
        created_at = tweet.get("created_at", "")
        image_info = None

        media = pick_first_image(tweet, media_by_key)
        if media:
            source_url = media.url or media.preview_image_url
            if source_url:
                ext = extension_from_url(source_url)
                local_file = IMAGE_DIR / f"{tweet_id}_1{ext}"
                download_file(source_url, local_file)
                image_info = {
                    "localPath": f"{PUBLIC_IMAGE_BASE}/{local_file.name}",
                    "alt": "X投稿画像"
                }

        posts.append({
            "id": tweet_id,
            "platform": "x",
            "title": "X最新情報",
            "date": created_at[:10] if created_at else "",
            "text": tweet.get("text", "").strip(),
            "url": f"https://x.com/{USERNAME}/status/{tweet_id}",
            "image": image_info,
        })

    jst = timezone(timedelta(hours=9))
    return {
        "account": USERNAME,
        "profileUrl": f"https://x.com/{USERNAME}",
        "updatedAt": datetime.now(jst).isoformat(timespec="seconds"),
        "imagePolicy": {
            "storage": "self-hosted",
            "directory": f"{PUBLIC_IMAGE_BASE}/",
            "maxImagesPerPost": 1
        },
        "posts": posts,
    }


def main() -> None:
    token = require_token()
    user_id = get_user_id(token)
    payload = fetch_posts(token, user_id)
    output = build_output(payload)

    if not output["posts"]:
        raise RuntimeError("投稿を取得できませんでした。既存JSONは更新しません。")

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"updated: {OUTPUT_JSON}")
    print(f"posts: {len(output['posts'])}")


if __name__ == "__main__":
    main()
