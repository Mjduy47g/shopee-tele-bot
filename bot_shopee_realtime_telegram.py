import json, requests, asyncio, logging, os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Konfigurasi dari Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_ADMIN = int(os.getenv("CHAT_ID_ADMIN", "0"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

PRODUCTS_FILE = "products.json"
logging.basicConfig(level=logging.INFO)

def load_products():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

def get_product_info(shopid, itemid):
    url = f"https://shopee.co.id/api/v4/item/get?itemid={itemid}&shopid={shopid}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json().get("data", {})
            if not data:
                return None
            return {
                "name": data.get("name", "Produk"),
                "stock": data.get("stock", 0),
                "url": f"https://shopee.co.id/product/{shopid}/{itemid}"
            }
    except Exception as e:
        logging.warning(f"Gagal ambil data Shopee: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Notifikasi Shopee aktif!\n"
        "Perintah:\n"
        "• /addproduk <shopid> <itemid>\n"
        "• /listproduk"
    )

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID_ADMIN:
        return await update.message.reply_text("Kamu bukan admin 😅")
    if len(context.args) != 2:
        return await update.message.reply_text("Format salah!\nContoh: /addproduk 987654321 1234567890")

    shopid, itemid = context.args
    products = load_products()
    for p in products:
        if p["shopid"] == int(shopid) and p["itemid"] == int(itemid):
            return await update.message.reply_text("Produk ini sudah ada di daftar.")

    info = get_product_info(shopid, itemid)
    if info:
        products.append({"shopid": int(shopid), "itemid": int(itemid), "last_stock": info["stock"], "name": info["name"]})
        save_products(products)
        await update.message.reply_text(f"✅ Ditambahkan: {info['name']}\n{info['url']}")
    else:
        await update.message.reply_text("❌ Gagal ambil data produk Shopee (cek shopid/itemid).")

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = load_products()
    if not products:
        return await update.message.reply_text("Belum ada produk yang dimonitor.")
    msg = "📦 *Daftar Produk yang Dimonitor:*\n"
    for p in products:
        msg += f"- {p['name']} (stok: {p['last_stock']})\nhttps://shopee.co.id/product/{p['shopid']}/{p['itemid']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def monitor_products(app):
    if CHAT_ID_ADMIN:
        await app.bot.send_message(chat_id=CHAT_ID_ADMIN, text="🤖 Bot Notifikasi Shopee AKTIF (24 jam)")
    while True:
        products = load_products()
        changed = False
        for p in products:
            info = get_product_info(p["shopid"], p["itemid"])
            if not info:
                continue
            if info["stock"] != p["last_stock"]:
                text = (
                    f"✅ *{info['name']}* READY ({info['stock']} pcs)\n{info['url']}"
                    if info["stock"] > 0 else
                    f"❌ *{info['name']}* HABIS\n{info['url']}"
                )
                if CHAT_ID_ADMIN:
                    await app.bot.send_message(chat_id=CHAT_ID_ADMIN, text=text, parse_mode="Markdown")
                p["last_stock"] = info["stock"]
                changed = True
        if changed:
            save_products(products)
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    if not TOKEN or not CHAT_ID_ADMIN:
        raise RuntimeError("Env TELEGRAM_BOT_TOKEN / CHAT_ID_ADMIN belum di-set.")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addproduk", add_product))
    app.add_handler(CommandHandler("listproduk", list_products))
    await app.start()
    await app.updater.start_polling(allowed_updates=['message'])
    asyncio.create_task(monitor_products(app))
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
