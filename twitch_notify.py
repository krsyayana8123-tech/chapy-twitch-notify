import os
import json
import urllib.request
import urllib.parse
import urllib.error

# =========================
# 設定
# =========================

TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

TWITCH_USER_LOGIN = "yuan_cos_"

STATE_FILE = "last_stream_id.txt"


# =========================
# HTTP処理
# =========================

def post_form(url, data):
    encoded = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "User-Agent": "chapy-twitch-notify/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"POST FORM ERROR: HTTP {e.code}")
        print(body)
        raise


def get_json(url, headers):
    headers = dict(headers)
    headers["User-Agent"] = "chapy-twitch-notify/1.0"

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"GET ERROR: HTTP {e.code}")
        print(body)
        raise


def post_json(url, data):
    body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "chapy-twitch-notify/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"DISCORD ERROR: HTTP {e.code}")
        print(body)
        raise


# =========================
# Twitchアクセストークン取得
# =========================

print("Twitchアクセストークン取得中...")

token_data = post_form(
    "https://id.twitch.tv/oauth2/token",
    {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
)

access_token = token_data["access_token"]

print("Twitch認証成功")


# =========================
# 配信状態取得
# =========================

stream_url = (
    "https://api.twitch.tv/helix/streams?"
    + urllib.parse.urlencode(
        {
            "user_login": TWITCH_USER_LOGIN
        }
    )
)

stream_data = get_json(
    stream_url,
    {
        "Client-Id": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
)


# =========================
# オフライン判定
# =========================

if not stream_data.get("data"):
    print(f"{TWITCH_USER_LOGIN} は現在オフラインです。")
    raise SystemExit(0)


# =========================
# 配信情報
# =========================

stream = stream_data["data"][0]

stream_id = stream["id"]

user_name = stream.get("user_name", TWITCH_USER_LOGIN)

title = stream.get("title") or "タイトルなし"

game_name = stream.get("game_name") or "カテゴリなし"

viewer_count = stream.get("viewer_count", 0)

twitch_url = f"https://www.twitch.tv/{TWITCH_USER_LOGIN}"

thumbnail_url = (
    stream.get("thumbnail_url", "")
    .replace("{width}", "1280")
    .replace("{height}", "720")
)

print("配信中です")
print(f"配信ID: {stream_id}")
print(f"タイトル: {title}")
print(f"ゲーム: {game_name}")


# =========================
# 前回通知した配信ID
# =========================

last_stream_id = ""

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last_stream_id = f.read().strip()


# =========================
# 重複通知防止
# =========================

if stream_id == last_stream_id:
    print("この配信はすでに通知済みです。")
    raise SystemExit(0)


# =========================
# Discord通知
# =========================

embed = {
    "title": title,
    "url": twitch_url,
    "description": (
        f"🎮 **{game_name}**\n"
        f"👀 視聴者数: **{viewer_count}**\n\n"
        f"▶️ [配信を見る]({twitch_url})"
    ),
    "footer": {
        "text": "Twitch 配信開始通知"
    }
}

if thumbnail_url:
    embed["image"] = {
        "url": thumbnail_url
    }


discord_data = {
    "username": "chapy",
    "content": (
        f"🔴 **{user_name} が配信を開始しました！**\n"
        f"{twitch_url}"
    ),
    "allowed_mentions": {
        "parse": []
    },
    "embeds": [
        embed
    ]
}


print("Discordへ通知中...")

status = post_json(
    DISCORD_WEBHOOK_URL,
    discord_data
)

print(f"Discord通知成功 HTTP {status}")


# =========================
# 通知済み配信ID保存
# =========================

with open(STATE_FILE, "w", encoding="utf-8") as f:
    f.write(stream_id)

print("配信IDを保存しました。")
print("処理完了！")
