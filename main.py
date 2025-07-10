import os
from keep_alive import keep_alive
keep_alive()

import asyncio
import nest_asyncio
import requests
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === Get Token from .env ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

# === Sensor His_ID Groups by Command ===
HIS_ID_GROUPS = {
    "NPK": ["10001", "10002", "10003", "10004", "10005", "10006", "10007"],
    "EC": ["20001", "10003"],
    "PH": ["30001", "10004"]
}

# === Sensor Labels & Types ===
SENSOR_MAPPING = {
    "10001": ("💧 Moisture", "m"),
    "10002": ("🌡️ Temperature (°C)", "t"),
    "10003": ("⚡ EC", "ec"),
    "20001": ("⚡ EC", "ec"),
    "10004": ("🧪 pH", "ph"),
    "30001": ("🧪 pH", "ph"),
    "10005": ("🌿 Nitrogen", "n"),
    "10006": ("🌿 Phosphorus", "p"),
    "10007": ("🌿 Potassium", "k")
}

# === WCOMMON Headers per Command (updated) ===
WCOMMON_MAP = {
    "NPK": { "cuid":"123456789","pid":"1","sv":"1.0","ts":1751945281000,"mt":255,"lan":"en","dap":"","sid":"621ba20bcef742b287aed3e7f4a2a95a","sign":"438d330dae5889dcfcf48c61b3130a92","domain":"asean.v-iec.com"
    },
    
    "EC": {"cuid":"123456789","pid":"1","sv":"1.0","ts":1751945410000,"mt":255,"lan":"en","dap":"","sid":"621ba20bcef742b287aed3e7f4a2a95a","sign":"438d330dae5889dcfcf48c61b3130a92","domain":"asean.v-iec.com"}
    ,
    "PH": {"cuid":"123456789","pid":"1","sv":"1.0","ts":1751945442000,"mt":255,"lan":"en","dap":"","sid":"621ba20bcef742b287aed3e7f4a2a95a","sign":"438d330dae5889dcfcf48c61b3130a92","domain":"asean.v-iec.com"}
}

# === dirId per Command ===
DIR_ID_MAP = {
    "NPK": "1",
    "EC": "2",
    "PH": "3"
}

# === Fetch Data Function ===
def fetch_data(command, his_ids):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://asean.v-iec.com",
        "Referer": "https://asean.v-iec.com/",
        "User-Agent": "Mozilla/5.0",
        "token": "null",
        
    }
    # ⬇️ Add this block right after headers = { ... }
    if command in ["EC", "PH"]:
        try:
            fetched = requests.get(f"http://127.0.0.1:7860/wcommon/{command.lower()}").json()
            headers["wcommon"] = json.dumps(fetched)
        except Exception as e:
            print(f"❌ Failed to fetch live wcommon for {command}: {e}")
            return {}
    else:
        headers["wcommon"] = json.dumps(WCOMMON_MAP[command])

    response = requests.post(
        "https://api.asean.v-iec.com/m2/hmiHisData/getHmiHisData",
        headers=headers,
        data={
            "deviceId": "20650",
            "dirId": DIR_ID_MAP[command],
            "hisCfgId": ",".join(his_ids),
            "orderByTime": 0,
            "pageIndex": 1,
            "pageSize": 10,
            "timeSelector": "",
            "prevOrNext": "",
            "startDate": "",
            "endDate": "",
            "type": ""
        }
    )

    print("🔴 Full Response:", response.text)

    try:
        result = response.json().get("result", {})
        print(f"✅ {command} Data Fetched:", json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ Failed to parse response: {e}")
        print("Raw response:", response.text)
        return {}

# === Recommendation Generator ===
def get_recommendation(value, sensor_type):
    try:
        value = float(value)
    except:
        return "No data."

    if sensor_type == "m":
        return "Low – irrigate." if value < 25.0 else "High – avoid overwatering must be below 55.0 ." if value > 55.0 else "Optimal moisture."
    if sensor_type == "t":
        return "Too cold – above 20." if value < 20 else "Too hot – below 34." if value > 34 else "Ideal temp."
    if sensor_type == "ec":
        return "Low EC – possible deficiency above 0.5." if value < 0.5 else "High EC – risk of salt stress below 2.0." if value > 2.0 else "EC OK."
    if sensor_type == "ph":
        return "Too acidic – lime recommended is above 5.8." if value < 5.8 else "Too alkaline – make it below 7.2." if value > 7.2 else "pH is good."
    if sensor_type == "n":
        return "Low N – fertilize make it above 40." if value < 40 else "Too much N – reduce input make it below 120." if value > 120 else "Nitrogen level good."
    if sensor_type == "p":
        return "Low P – fertilize make it above 15." if value < 15 else "Too much P – reduce input make it below 50." if value > 50 else "Phosphorus OK."
    if sensor_type == "k":
        return "Low K – fertilize make it above 60 ." if value < 60 else "Too much K – reduce input make it below 250." if value > 250 else "Potassium OK."

    return "No recommendation."

# === Bot Start Handler ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["NPK"], ["EC"], ["PH"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_text(
        "👋 Welcome to PapaYa Bot!\nPlease select a command below:",
        reply_markup=reply_markup
    )

# === Main Command Handler ===
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.upper()

    if cmd not in HIS_ID_GROUPS:
        await update.message.reply_text("❓ Unknown command. Try NPK, EC, or PH.")
        return

    his_ids = HIS_ID_GROUPS[cmd]
    data = fetch_data(cmd, his_ids)

    if not data or all(not v.get("list") for v in data.values() if isinstance(v, dict)):
        await update.message.reply_text("⚠️ No data returned from the server.")
        return

    msg = f"📡 Plot PapaYa Sensor Readings:\n"
    printed_time = False

    for entry in data.values():
        if not isinstance(entry, dict) or not entry.get("list"):
            continue

        latest = entry["list"][0]
        his_id = latest.get("his_uid") or latest.get("his_id")
        value = latest.get("value", "N/A")
        time = latest.get("monitor_time_show", "N/A")

        if his_id not in SENSOR_MAPPING:
            continue

        label, stype = SENSOR_MAPPING[his_id]
        advice = get_recommendation(value, stype)

        if not printed_time:
            msg += f"🕒 Time: {time}\n\n"
            printed_time = True

        msg += f"{label}: {value} → {advice}\n"

    await update.message.reply_text(msg)

# === Start Polling ===
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_command))

    print("✅ PapaYa Bot is running with polling.")
    await app.run_polling()

# === Entrypoint ===
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(run_bot())
