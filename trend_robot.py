"""
Trading Robot 2.0 - TradingView webhook -> Telegram (@trend_robot_2_bot)

TUZATISHLAR (timeout muammosi):
  1) Webhook darhol 200 qaytaradi, Telegram'ga yuborish orqa fonda (thread)
  2) Keep-alive: server o'ziga har 10 daqiqada ping yuboradi (Render uxlamasin)
  3) Telegram so'rovi qisqa timeout + 2 marta qayta urinish
  4) Whitelist olib tashlandi - HAMMA juftliklardan signal o'tadi
  5) Xabar sarlavhasi olib tashlandi, tf H1 ko'rinishida

Render Environment:
  BOT_TOKEN  = @BotFather bergan token
  CHAT_IDS   = 592897593,-1002943529696

Start command:
  gunicorn trend_robot:app
"""

import os
import json
import time
import threading
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_IDS = [c.strip() for c in os.environ.get("CHAT_IDS", "").split(",") if c.strip()]

TG_URL = "https://api.telegram.org/bot{}/sendMessage"

# Keep-alive uchun Render avtomatik beradigan manzil
SELF_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PING_SECONDS = 600


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_IDS:
        print("BOT_TOKEN yoki CHAT_IDS yo'q")
        return

    for chat_id in CHAT_IDS:
        for attempt in range(2):
            try:
                r = requests.post(
                    TG_URL.format(BOT_TOKEN),
                    json={"chat_id": chat_id, "text": text},
                    timeout=8,
                )
                if r.status_code == 200:
                    break
                print("Telegram xato", chat_id, r.status_code, r.text[:200])
            except Exception as e:
                print("Telegram istisno", chat_id, e)
            time.sleep(1)


def pretty_tf(tf):
    """M60 -> H1, M240 -> H4, M15 -> M15, D -> D1"""
    t = str(tf).strip().upper()
    if t.startswith("M") and t[1:].isdigit():
        m = int(t[1:])
        if m % 60 == 0 and m >= 60:
            return "H{}".format(m // 60)
        return "M{}".format(m)
    if t == "D":
        return "D1"
    if t == "W":
        return "W1"
    return t


def build_message(data):
    symbol = data.get("symbol", "?")
    tf = pretty_tf(data.get("tf", "?"))
    side = str(data.get("side", "?")).upper()
    brk = data.get("breakType", "")
    price = data.get("price", "")

    emoji = "\U0001F7E2" if side == "BUY" else "\U0001F534"

    lines = [
        "{} {} {} {}".format(emoji, symbol, tf, side),
    ]
    if brk:
        lines.append("{} BREAKOUT".format(brk))
    if price:
        lines.append("Narx: {}".format(price))
    return "\n".join(lines)


@app.route("/", methods=["GET", "HEAD"])
def health():
    return "Trading Robot 2.0 ishlayapti"


@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "pong"


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    raw = request.get_data(as_text=True) or ""

    try:
        data = json.loads(raw)
    except Exception:
        print("JSON emas:", raw[:300])
        return "bad json", 200

    text = build_message(data)

    # Telegram'ga yuborish orqa fonda - TradingView kutib qolmaydi
    threading.Thread(target=send_telegram, args=(text,), daemon=True).start()

    return "ok", 200


def keep_alive():
    if not SELF_URL:
        print("RENDER_EXTERNAL_URL yo'q - keep-alive o'chirilgan")
        return
    url = SELF_URL.rstrip("/") + "/ping"
    while True:
        time.sleep(PING_SECONDS)
        try:
            requests.get(url, timeout=10)
        except Exception as e:
            print("ping xato", e)


threading.Thread(target=keep_alive, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
"""
Trading Robot 2.0 - TradingView webhook -> Telegram (@trend_robot_2_bot)

TUZATISHLAR (timeout muammosi):
  1) Webhook darhol 200 qaytaradi, Telegram'ga yuborish orqa fonda (thread)
  2) Keep-alive: server o'ziga har 10 daqiqada ping yuboradi (Render uxlamasin)
  3) Telegram so'rovi qisqa timeout + 2 marta qayta urinish
  4) Whitelist olib tashlandi - HAMMA juftliklardan signal o'tadi

Render Environment:
  BOT_TOKEN  = @BotFather bergan token
  CHAT_IDS   = 592897593,-1002943529696

Start command:
  gunicorn trend_robot:app
"""

import os
import json
import time
import threading
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_IDS = [c.strip() for c in os.environ.get("CHAT_IDS", "").split(",") if c.strip()]

TG_URL = "https://api.telegram.org/bot{}/sendMessage"

# Keep-alive uchun Render avtomatik beradigan manzil
SELF_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PING_SECONDS = 600


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_IDS:
        print("BOT_TOKEN yoki CHAT_IDS yo'q")
        return

    for chat_id in CHAT_IDS:
        for attempt in range(2):
            try:
                r = requests.post(
                    TG_URL.format(BOT_TOKEN),
                    json={"chat_id": chat_id, "text": text},
                    timeout=8,
                )
                if r.status_code == 200:
                    break
                print("Telegram xato", chat_id, r.status_code, r.text[:200])
            except Exception as e:
                print("Telegram istisno", chat_id, e)
            time.sleep(1)


def build_message(data):
    symbol = data.get("symbol", "?")
    tf = data.get("tf", "?")
    side = str(data.get("side", "?")).upper()
    brk = data.get("breakType", "")
    price = data.get("price", "")

    emoji = "\U0001F7E2" if side == "BUY" else "\U0001F534"

    lines = [
        "\U0001F916 Trading Robot 2.0",
        "{} {} {} {}".format(emoji, symbol, tf, side),
    ]
    if brk:
        lines.append("{} BREAKOUT".format(brk))
    if price:
        lines.append("Narx: {}".format(price))
    return "\n".join(lines)


@app.route("/", methods=["GET", "HEAD"])
def health():
    return "Trading Robot 2.0 ishlayapti"


@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "pong"


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    raw = request.get_data(as_text=True) or ""

    try:
        data = json.loads(raw)
    except Exception:
        print("JSON emas:", raw[:300])
        return "bad json", 200

    text = build_message(data)

    # Telegram'ga yuborish orqa fonda - TradingView kutib qolmaydi
    threading.Thread(target=send_telegram, args=(text,), daemon=True).start()

    return "ok", 200


def keep_alive():
    if not SELF_URL:
        print("RENDER_EXTERNAL_URL yo'q - keep-alive o'chirilgan")
        return
    url = SELF_URL.rstrip("/") + "/ping"
    while True:
        time.sleep(PING_SECONDS)
        try:
            requests.get(url, timeout=10)
        except Exception as e:
            print("ping xato", e)


threading.Thread(target=keep_alive, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
