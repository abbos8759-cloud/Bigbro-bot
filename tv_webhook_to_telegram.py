"""
TradingView webhook -> Telegram relay.

Faqat 2 ta narsani o'zgartiring: BOT_TOKEN va CHAT_ID.
BOT_TOKEN   -> Telegram'da @BotFather orqali olinadi (/newbot)
CHAT_ID     -> @userinfobot ga /start yozib olinadi (bu SIZ - botning egasi/admini)

OBUNACHILAR (yangi):
Endi botga kimdir /start yozsa, u avtomatik "obunachi" bo'lib qo'shiladi va
barcha signal xabarlari unga ham yuboriladi. Buning uchun Telegram'ga bir marta
webhook o'rnatish kerak (pastdagi "TELEGRAM WEBHOOK O'RNATISH" bo'limiga qarang).

Siz (egasi/CHAT_ID) botga oddiy xabar yozsangiz (buyruq bo'lmasa), o'sha xabar
"📢" belgisi bilan BARCHA obunachilarga yuboriladi - shu orqali siz ham
obunachilar ko'radigan xabar yoza olasiz.

DIQQAT: obunachilar ro'yxati (subscribers.json) serverning diskida saqlanadi.
Render'ning bepul tarifida bu fayl har safar YANGI kod deploy qilinganda
(GitHub'ga push qilinganda) TOZALANISHI mumkin - shunda obunachilar yana
/start bosishi kerak bo'ladi. Doimiy saqlash kerak bo'lsa, keyinchalik
kichik bir bazaga (masalan Render Postgres) o'tkazish mumkin.

Ishga tushirish (lokal test uchun):
    pip install flask requests
    python tv_webhook_to_telegram.py

Keyin TradingView alert -> Webhook URL maydoniga shu serverning ochiq manzilini yozasiz:
    https://<domeningiz>/tv-webhook

TELEGRAM WEBHOOK O'RNATISH (bir marta, deploy bo'lgandan keyin):
    https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<domeningiz>/telegram-webhook
Shu manzilni brauzerda ochsangiz yetarli - Telegram javobida "ok": true chiqishi kerak.
"""

import json
import os
import threading

import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8956959821:AAH6457PLHjQKRISM_VgwnUHbyKhC8YgTvA")
CHAT_ID = os.environ.get("CHAT_ID", "592897593")  # botning egasi (admin)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscribers.json")

_lock = threading.Lock()

# Signal beriladigan belgilar ro'yxati. Olib tashlash uchun qatorni o'chiring,
# qo'shish uchun yangi qator qo'shing (TradingView'dagi syminfo.ticker bilan bir xil
# bo'lishi kerak, masalan "EURUSD", "XAUUSD", "BTCUSDT.P", "NAS100", "GER40",
# "JP225", "USDJPY", "AUDUSD"). Bo'sh qoldirilsa (SYMBOLS_WHITELIST = None) -
# har qanday belgidan kelgan signal o'tkaziladi.
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


def load_subscribers() -> set:
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, ValueError):
        return set()


def save_subscribers(ids: set) -> None:
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(ids), f)


def add_subscriber(chat_id) -> None:
    with _lock:
        ids = load_subscribers()
        if chat_id not in ids:
            ids.add(chat_id)
            save_subscribers(ids)


def remove_subscriber(chat_id) -> None:
    with _lock:
        ids = load_subscribers()
        if chat_id in ids:
            ids.discard(chat_id)
            save_subscribers(ids)


def all_recipients() -> set:
    """Egasi (CHAT_ID) + barcha obuna bo'lgan chat_id'lar."""
    ids = load_subscribers()
    try:
        ids.add(int(CHAT_ID))
    except (TypeError, ValueError):
        ids.add(CHAT_ID)
    return ids


def send_telegram(chat_id, text: str) -> bool:
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def broadcast(text: str) -> None:
    for chat_id in all_recipients():
        send_telegram(chat_id, text)


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

    broadcast(message)
    return "ok", 200


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    """Telegram'dan kelgan xabarlarni qabul qiladi (/start, /stop va egasining
    oddiy xabarlari). Ishlashi uchun bir marta setWebhook chaqirilishi kerak
    (fayl boshidagi izohga qarang)."""
    update = request.get_json(silent=True) or {}
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return "ok", 200

    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()

    if chat_id is None:
        return "ok", 200

    if text == "/start":
        add_subscriber(chat_id)
        send_telegram(chat_id, "✅ Siz BigBro Trading Bot signallariga obuna bo'ldingiz!")
        return "ok", 200

    if text == "/stop":
        remove_subscriber(chat_id)
        send_telegram(chat_id, "❌ Obuna bekor qilindi. Qayta obuna bo'lish uchun /start yozing.")
        return "ok", 200

    # Botning egasi yozgan har qanday boshqa xabar - barcha obunachilarga yuboriladi
    if str(chat_id) == str(CHAT_ID) and text:
        broadcast(f"📢 {text}")

    return "ok", 200


@app.route("/", methods=["GET"])
def health():
    return "BigBro Trading Bot ishlayapti", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
