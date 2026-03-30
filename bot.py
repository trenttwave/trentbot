import os
import re
import json
import time
import base64
import hashlib
import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
HACOO_COOKIE = os.environ.get("HACOO_COOKIE", "").strip()
CHANNEL_ID = os.environ.get("CHANNEL_ID", "").strip()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"


def gemini_text(prompt: str) -> str:
    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    logger.info(f"Gemini text status: {resp.status_code} - {resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def gemini_vision(image_bytes: bytes, prompt: str) -> str:
    image_b64 = base64.b64encode(image_bytes).decode()
    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
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
    logger.info(f"Gemini vision status: {resp.status_code} - {resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse_f_tracking(cookie: str) -> str | None:
    """Extract affiliate tracking from the f cookie value.

    Example f cookie: p_aff.o_charmmcn2409.g_affiliate-coupon.m_trenttwave.c_aid-124516-aog-x-aoge.t_20251005-164022.v_1
    Returns the parts relevant for affiliate tracking (strips timestamp/version).
    """
    match = re.search(r'(?:^|;\s*)f=([^;]+)', cookie)
    if not match:
        return None
    f_value = match.group(1).strip()
    # Keep all parts except session-specific timestamp (t_) and version (v_)
    parts = [p for p in f_value.split('.') if not p.startswith('t_') and not p.startswith('v_')]
    return '.'.join(parts) if parts else None


def _make_sign(params: dict) -> str:
    sorted_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.md5(sorted_string.encode()).hexdigest()


def _try_promo_link_api(product_url: str) -> str | None:
    """Attempt to get a short affiliate link from the Hacoo promoLink API.
    Returns None if the API fails or returns an error code.
    """
    api_url = "https://gw.hacoo.app/gw/dwp.aff-home-core.promoLink/1"
    ct = str(int(time.time() * 1000))
    params = {
        "data": json.dumps({"link": product_url}, separators=(",", ":")),
        "gw_ver": "1",
        "ct": ct,
        "plat": "pc",
        "appname": "saramart",
    }
    sign = _make_sign(params)
    logger.info(f"PromoLink sign: {sign} | params: {'&'.join(f'{k}={v}' for k,v in sorted(params.items()))}")
    headers = {
        "Cookie": HACOO_COOKIE,
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Origin": "https://affiliate.hacoo.app",
        "Referer": "https://affiliate.hacoo.app/",
        "Accept": "application/json, text/plain, */*",
    }
    data = {**params, "sign": sign}
    resp = requests.post(api_url, data=data, headers=headers, params={"sid": "9"}, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    logger.info(f"PromoLink API response: {result}")
    if result.get("code") not in (200, 0, "200", "0", None) or result.get("code") == 3012:
        logger.warning(f"PromoLink API error code {result.get('code')}: {result.get('msg') or result.get('message', '')}")
        return None
    data_field = result.get("data") or result.get("result") or {}
    if isinstance(data_field, dict):
        return (
            data_field.get("short_url")
            or data_field.get("link")
            or data_field.get("url")
            or data_field.get("shortUrl")
        )
    return None


def generate_affiliate_link(product_id: str) -> str:
    """Generate an affiliate link for a Hacoo product ID.

    Tries the promoLink API first. If it fails (e.g. sign check error),
    falls back to constructing a direct affiliate URL using the f-cookie tracking value.
    """
    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"

    # 1. Try the official promoLink API
    try:
        link = _try_promo_link_api(product_url)
        if link:
            logger.info(f"PromoLink API success: {link}")
            return link
    except Exception as e:
        logger.warning(f"PromoLink API exception: {e}")

    # 2. Fallback: direct URL with affiliate f-cookie tracking parameter
    f_tracking = _parse_f_tracking(HACOO_COOKIE)
    if f_tracking:
        direct_link = f"{product_url}?f={f_tracking}"
        logger.info(f"Using direct affiliate link: {direct_link}")
        return direct_link

    # 3. Last resort: plain product URL
    logger.warning("No affiliate tracking found in cookie, returning plain URL")
    return product_url


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Soy TrentBot.\n\n"
        "Enviame una captura de un producto de Hacoo y te generare el link de afiliado."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("Analizando la imagen...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        product_id = gemini_vision(
            image_bytes,
            (
                "Analiza esta captura de pantalla de la app Hacoo. "
                "Extrae SOLO el ID numerico del producto "
                "(normalmente visible debajo del nombre del producto, ejemplo: 40140156). "
                "Responde unicamente con el numero, sin texto adicional."
            ),
        ).strip()

        if not product_id.isdigit():
            await status_msg.edit_text(
                "No encontre el ID del producto. Asegurate de que la captura muestre el ID numerico."
            )
            return

        await status_msg.edit_text(f"ID encontrado: {product_id}\nGenerando link de afiliado...")

        affiliate_link = generate_affiliate_link(product_id)

        reply_text = f"ID del producto: `{product_id}`\n\nLink de afiliado:\n{affiliate_link}"
        await status_msg.edit_text(reply_text, parse_mode="Markdown")

        # Post to channel if configured
        if CHANNEL_ID:
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=affiliate_link,
                )
                logger.info(f"Posted affiliate link to channel {CHANNEL_ID}")
            except Exception as e:
                logger.error(f"Failed to post to channel {CHANNEL_ID}: {e}")

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await status_msg.edit_text(f"Error: {e}")


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
        await update.message.reply_text("Error al procesar tu mensaje. Intentalo de nuevo.")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")
    if not HACOO_COOKIE:
        raise ValueError("HACOO_COOKIE is not set")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
