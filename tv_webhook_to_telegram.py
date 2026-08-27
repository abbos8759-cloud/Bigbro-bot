"""
TradingView webhook -> Telegram relay.

Faqat 2 ta narsani o'zgartiring: BOT_TOKEN va CHAT_ID.
BOT_TOKEN   -> Telegram'da @BotFather orqali olinadi (/newbot)
CHAT_ID     -> @userinfobot ga /start yozib olinadi (shaxsiy chat uchun)
              yoki guruh/kanal uchun @RawDataBot orqali olinadi

Ishga tushirish (lokal test uchun):
    pip install flask requests
    python tv_webhook_to_telegram.py

Keyin TradingView alert -> Webhook URL maydoniga shu serverning ochiq manzilini yozasiz:
    https://<domeningiz>/tv-webhook
"""

import json
import os

import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8956959821:AAH6457PLHjQKRISM_VgwnUHbyKhC8YgTvA")
CHAT_ID = os.environ.get("CHAT_ID", "592897593")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Signal beriladigan belgilar ro'yxati. Olib tashlash uchun qatorni o'chiring,
# qo'shish uchun yangi qator qo'shing (TradingView'dagi syminfo.ticker bilan bir xil
# bo'lishi kerak, masalan "EURUSD", "XAUUSD", "BTCUSDT.P", "NAS100", "GER40",
# "JP225", "USDJPY", "AUDUSD"). Bo'sh qoldirilsa (SYMBOLS_WHITELIST = None) -
# har qanday belgidan kelgan signal o'tkaziladi.
SYMBOLS_WHITELIST = {
    "XAUUSD",
    "BTCUSDT.P",
    "GER40",
    "JP225",
    "USDJPY",
    "EURUSD",
    "AUDUSD",
}


def format_message(raw_text: str):
    """TradingView alert JSON ni "EURUSD M30 BUY / RESISTANCE BREAKOUT"
    ko'rinishidagi Telegram xabariga aylantiradi. Ruxsat etilmagan belgi bo'lsa None qaytaradi.
    Signal endi FAQAT support/resistance chizig'i sham tanasi bilan yorib yopilganda keladi
    (EMA endi shartga kirmaydi, faqat grafikda ko'rish uchun qoladi)."""
    try:
        data = json.loads(raw_text)
        symbol = data["symbol"]
        tf = data["tf"]
        side = data["side"]
        break_type = data["breakType"]
    except (ValueError, TypeError, KeyError):
        return raw_text or "Signal keldi"

    if SYMBOLS_WHITELIST and symbol not in SYMBOLS_WHITELIST:
        return None

    emoji = "🟢" if side == "BUY" else "🔴"
    return (
        f"🤖 BigBro Trading Bot\n"
        f"{emoji} {symbol} {tf} {side}\n"
        f"{break_type} BREAKOUT"
    )


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    raw_text = request.get_data(as_text=True)
    message = format_message(raw_text)

    if message is None:
        return "skipped: symbol not in whitelist", 200

    resp = requests.post(
        TELEGRAM_URL,
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10,
    )

    if resp.status_code != 200:
        return f"telegram error: {resp.text}", 500

    return "ok", 200


@app.route("/", methods=["GET"])
def health():
    return "BigBro Trading Bot ishlayapti", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
