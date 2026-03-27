import os
import io
import json
import time
import base64
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
HACOO_GW_TOKEN = os.environ.get("HACOO_GW_TOKEN")

GEMINI_TEXT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
GEMINI_VISION_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"


def gemini_text(prompt: str) -> str:
    resp = requests.post(
        f"{GEMINI_TEXT_URL}?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    logger.info(f"Gemini text status: {resp.status_code} - {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def gemini_vision(image_bytes: bytes, prompt: str) -> str:
    image_b64 = base64.b64encode(image_bytes).decode()
    resp = requests.post(
        f"{GEMINI_VISION_URL}?key={GEMINI_API_KEY}",
        json={
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                    {"text": prompt},
                ]
            }]
        },
        timeout=30,
    )
    logger.info(f"Gemini vision status: {resp.status_code} - {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Soy TrentBot.\n\n"
        "Enviame una captura de un producto de Hacoo y te generare el link de afiliado "
        "con las fotos del producto, listo para publicar en el canal.\n\n"
        "Tambien puedes escribirme cualquier pregunta."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/help - Ver este mensaje de ayuda\n\n"
        "Enviame una captura de un producto de Hacoo y te dare el link de afiliado "
        "con sus fotos, listo para publicar en el canal."
    )


async def extract_product_id(image_bytes: bytes) -> str:
    return gemini_vision(
        image_bytes,
        (
            "Analiza esta captura de pantalla de la app Hacoo. "
            "Extrae SOLO el ID numerico del producto "
            "(normalmente visible debajo del nombre del producto, ejemplo: 40140156). "
            "Responde unicamente con el numero, sin texto adicional."
        ),
    ).strip()


def scrape_product_images(product_id: str) -> list:
    url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    image_urls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if src and ("product" in src or "goods" in src or "item" in src) and src.startswith("http"):
            if src not in image_urls:
                image_urls.append(src)
        if len(image_urls) >= 6:
            break
    return image_urls


def generate_affiliate_link(product_id: str) -> str:
    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
    api_url = "https://gw.hacoo.app/gw/dwp-home-core.promoLink/1"
    headers = {
        "Cookie": f"gw-token={HACOO_GW_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    data = {
        "data": json.dumps({"link": product_url}),
        "gw_ver": "1",
        "ct": str(int(time.time() * 1000)),
        "plat": "pc",
        "appname": "saramart",
    }
    resp = requests.post(api_url, data=data, headers=headers, params={"sid": "12"}, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    logger.info(f"Affiliate API response: {result}")
    data_field = result.get("data") or result.get("result") or result
    if isinstance(data_field, dict):
        link = (
            data_field.get("short_url")
            or data_field.get("link")
            or data_field.get("url")
            or data_field.get("shortUrl")
        )
        if link:
            return link
    raise ValueError(f"Could not extract link from response: {result}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("Analizando la imagen...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        product_id = await extract_product_id(image_bytes)
        if not product_id.isdigit():
            await status_msg.edit_text(
                "No he podido encontrar el ID del producto en la imagen. "
                "Asegurate de que la captura muestre el ID numerico."
            )
            return

        logger.info(f"Product ID: {product_id}")
        await status_msg.edit_text(
            f"Producto {product_id} encontrado. Descargando fotos y generando link..."
        )

        image_urls = scrape_product_images(product_id)
        affiliate_link = generate_affiliate_link(product_id)

        context.user_data["pending"] = {
            "product_id": product_id,
            "image_urls": image_urls,
            "affiliate_link": affiliate_link,
        }

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Si, publicar en el canal", callback_data="publish_yes"),
            InlineKeyboardButton("No", callback_data="publish_no"),
        ]])

        preview_text = (
            f"Producto: {product_id}\n"
            f"Link de afiliado:\n{affiliate_link}\n\n"
            f"Fotos encontradas: {len(image_urls)}\n\n"
            "Publico esto en el canal?"
        )

        await status_msg.delete()
        await update.message.reply_text(preview_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await status_msg.edit_text(
            "Lo siento, hubo un error procesando la imagen. Intentalo de nuevo."
        )


async def handle_publish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "publish_no":
        await query.edit_message_text("Publicacion cancelada.")
        context.user_data.pop("pending", None)
        return

    pending = context.user_data.get("pending")
    if not pending:
        await query.edit_message_text("No hay ninguna publicacion pendiente.")
        return

    await query.edit_message_text("Publicando en el canal...")

    image_urls = pending["image_urls"]
    affiliate_link = pending["affiliate_link"]
    caption = affiliate_link

    try:
        if image_urls:
            media_group = [
                InputMediaPhoto(media=url, caption=caption if i == 0 else "")
                for i, url in enumerate(image_urls[:10])
            ]
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media_group)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=caption)

        await query.edit_message_text("Publicado en el canal correctamente.")
        context.user_data.pop("pending", None)

    except Exception as e:
        logger.error(f"Error publishing to channel: {e}")
        await query.edit_message_text(
            "Error al publicar en el canal. Verifica que el bot sea administrador del canal."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.first_name} (@{user.username}): {user_message}")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        reply = gemini_text(user_message)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        await update.message.reply_text(
            "Lo siento, hubo un error procesando tu mensaje. Intentalo de nuevo."
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    if not HACOO_GW_TOKEN:
        raise ValueError("HACOO_GW_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_publish_callback, pattern="^publish_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
