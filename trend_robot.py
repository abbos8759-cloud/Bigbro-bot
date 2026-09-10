"""
Trading Robot 2.0 — TradingView webhook -> Telegram (@trend_robot_2_bot)

Ish jarayoni:
  TradingView alert -> POST /tv-webhook -> shu server -> Telegram

Render Environment o'zgaruvchilari (kodda TOKEN yozilmaydi!):
  BOT_TOKEN  = @BotFather bergan token
  CHAT_IDS   = 592897593,-1002943529696   (vergul bilan, probelsiz)

Start command:
  gunicorn trend_robot:app
"""

import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_NAME = "@trend_robot_2_bot"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_IDS = [c.strip() for c in os.environ.get("CHAT_IDS", "").split(",") if c.strip()]

# Faqat shu ikkita belgi uchun signal yuboriladi
WHITELIST = {"XAUUSD", "BTCUSDT.P"}

TG_URL = "https://api.telegram.org/bot{}/sendMessage"


def send_telegram(text):
    """Har bir chat ID ga xabar yuboradi. Bittasi ham xato bersa False qaytaradi."""
    if not BOT_TOKEN or not CHAT_IDS:
        print("BOT_TOKEN yoki CHAT_IDS yo'q")
        return False

    ok = True
    for chat_id in CHAT_IDS:
        try:
            r = requests.post(
                TG_URL.format(BOT_TOKEN),
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
            if r.status_code != 200:
                print("Telegram xato", chat_id, r.status_code, r.text)
                ok = False
        except Exception as e:
            print("Telegram istisno", chat_id, e)
            ok = False
    return ok


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


@app.route("/", methods=["GET"])
def health():
    return "Trading Robot 2.0 ishlayapti"


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    raw = request.get_data(as_text=True) or ""

    try:
        data = json.loads(raw)
    except Exception:
        print("JSON emas:", raw[:300])
        return "bad json", 400

    symbol = str(data.get("symbol", "")).strip().upper()

    if symbol not in WHITELIST:
        print("skipped:", symbol)
        return "skipped: symbol not in whitelist", 200

    text = build_message(data)
    if send_telegram(text):
        return "ok", 200
    return "telegram error", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
