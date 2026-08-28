"""
TradingView webhook -> Telegram relay.

MUHIM (xavfsizlik): BOT_TOKEN kod ichida YOZILMAYDI - u Render'ning
"Environment" bo'limida maxfiy o'zgaruvchi sifatida saqlanadi. Sabab: bu fayl
public GitHub repo'da, va tokenni kodga yozib qo'ysangiz, uni har kim ko'rib,
botingizni o'zlashtirib olishi mumkin.

BOT_TOKEN   -> Render -> Environment -> BOT_TOKEN = <@BotFather'dan olingan token>
CHAT_IDS    -> Xabarlar yuboriladigan manzillar (vergul bilan ajratilgan, bir nechta
               bo'lishi mumkin - masalan bot xususiy chat HAM, kanal HAM):
               - Shaxsiy chat uchun: @userinfobot ga /start yozib o'z ID'ingizni oling.
               - KANAL uchun: kanal yarating, botni "Post messages" huquqi bilan
                 admin qilib qo'shing, kanalning chat_id'sini oling.
               Kanalda obunachilar SIGNALLARGA REAKSIYA (👍❤️ va h.k.) bosa oladi,
               lekin YOZA OLMAYDI. Shaxsiy chatda esa signal xuddi shu vaqtda
               botning o'zida ham ko'rinadi. Standart holatda ikkalasiga ham
               yuboriladi: bot xususiy chat (592897593) va "BigBro Traders"
               kanali (-1002943529696).

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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Standart: bot bilan xususiy chat (592897593) VA "BigBro Traders" kanali
# (-1002943529696) - ikkalasiga ham signal boradi. Render'da CHAT_IDS
# o'zgaruvchisini o'rnatib, vergul bilan ajratib xohlagan manzillarni
# ko'rsatish mumkin (masalan: "592897593,-1002943529696,-100...").
_default_chat_ids = "592897593,-1002943529696"
CHAT_IDS = [
    c.strip() for c in os.environ.get("CHAT_IDS", _default_chat_ids).split(",") if c.strip()
]

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable topilmadi! "
        "Render -> Settings -> Environment -> Add Environment Variable orqali qo'shing."
    )

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Signal beriladigan belgilar ro'yxati. Olib tashlash uchun qatorni o'chiring,
# qo'shish uchun yangi qator qo'shing (TradingView'dagi syminfo.ticker bilan bir xil
# bo'lishi kerak). Bo'sh qoldirilsa (SYMBOLS_WHITELIST = None) - har qanday
# belgidan kelgan signal o'tkaziladi.
SYMBOLS_WHITELIST = {
    "XAUUSD",
    "XAGUSD",
    "BTCUSDT.P",
    "BNBUSDT.P",
    "SOLUSDT.P",
    "BCHUSDT.P",
    "GER40",
    "JP225",
    "USDJPY",
    "EURUSD",
    "AUDUSD",
    "SPX500",
    "NAS100",
    "EU50",
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

    errors = []
    for chat_id in CHAT_IDS:
        resp = requests.post(
            TELEGRAM_URL,
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        if resp.status_code != 200:
            errors.append(f"{chat_id}: {resp.text}")

    if errors:
        return "telegram error(s): " + " | ".join(errors), 500

    return "ok", 200


@app.route("/", methods=["GET"])
def health():
    return "BigBro Trading Bot ishlayapti", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
