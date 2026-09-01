import os
import json
import urllib.request
import urllib.parse

TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

TWITCH_USER_LOGIN = "yuan_cos_"
STATE_FILE = "last_stream_id.txt"


def post_form(url, data):
    encoded = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded,
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url, headers):
    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url, data):
    body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status


# Twitchのアクセストークン取得
token_data = post_form(
    "https://id.twitch.tv/oauth2/token",
    {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
)

access_token = token_data["access_token"]


# 配信状態を取得
stream_url = (
    "https://api.twitch.tv/helix/streams?"
    + urllib.parse.urlencode({
        "user_login": TWITCH_USER_LOGIN
    })
)

stream_data = get_json(
    stream_url,
    {
        "Client-Id": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
)


# オフラインなら終了
if not stream_data["data"]:
    print(f"{TWITCH_USER_LOGIN} は現在オフラインです。")
    raise SystemExit(0)


stream = stream_data["data"][0]

stream_id = stream["id"]
user_name = stream["user_name"]
title = stream["title"] or "タイトルなし"
game_name = stream["game_name"] or "カテゴリなし"
viewer_count = stream["viewer_count"]

twitch_url = f"https://www.twitch.tv/{stream['user_login']}"

thumbnail_url = (
    stream["thumbnail_url"]
    .replace("{width}", "1280")
    .replace("{height}", "720")
)


# 前回通知した配信IDを読む
last_stream_id = ""

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last_stream_id = f.read().strip()


# 同じ配信なら何もしない
if stream_id == last_stream_id:
    print("この配信はすでに通知済みです。")
    raise SystemExit(0)


# Discordへ通知
discord_data = {
    "username": "chapy",
    "content": f"🔴 **{user_name} が配信を開始しました！**\n{twitch_url}",
    "allowed_mentions": {
        "parse": []
    },
    "embeds": [
        {
            "title": title,
            "url": twitch_url,
            "description": (
                f"🎮 **{game_name}**\n"
                f"👀 視聴者数: {viewer_count}"
            ),
            "image": {
                "url": thumbnail_url
            },
            "footer": {
                "text": "Twitch 配信開始通知"
            }
        }
    ]
}

post_json(DISCORD_WEBHOOK_URL, discord_data)

print(f"Discordに通知しました: {title}")


# 通知成功後に今回の配信IDを保存
with open(STATE_FILE, "w", encoding="utf-8") as f:
    f.write(stream_id)
