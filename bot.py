import os
import base64
import logging
import asyncio
from anthropic import Anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
HACOO_EMAIL = os.environ.get("HACOO_EMAIL")
HACOO_PASSWORD = os.environ.get("HACOO_PASSWORD")

client = Anthropic(api_key=ANTHROPIC_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\u00a1Hola! Soy TrentBot.\n\n"
        "Env\u00edame una captura de un producto de Hacoo y te generar\u00e9 el link de afiliado autom\u00e1ticamente.\n\n"
        "Tambi\u00e9n puedes escribirme cualquier pregunta."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/help - Ver este mensaje de ayuda\n\n"
        "Env\u00edame una foto de un producto de Hacoo y te dar\u00e9 el link de afiliado."
    )


async def extract_product_id(image_bytes: bytes) -> str:
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analiza esta captura de pantalla de la app Hacoo. "
                            "Extrae SOLO el ID num\u00e9rico del producto "
                            "(normalmente visible debajo del nombre del producto, ejemplo: 40140156). "
                            "Responde \u00danicamente con el n\u00famero, sin texto adicional."
                        ),
                    },
                ],
            }
        ],
    )
    product_id = response.content[0].text.strip()
    return product_id


async def generate_affiliate_link(product_id: str) -> str:
    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://affiliate.hacoo.app/en-ES/login", timeout=30000)
            await page.wait_for_load_state("networkidle")
            await page.fill("input[type='email'], input[name='email'], input[placeholder*='email' i]", HACOO_EMAIL)
            await page.fill("input[type='password'], input[name='password']", HACOO_PASSWORD)
            await page.click("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')")
            await page.wait_for_load_state("networkidle")
            await page.goto("https://affiliate.hacoo.app/en-ES/promotion/link", timeout=30000)
            await page.wait_for_load_state("networkidle")
            textarea = page.locator("textarea, input[type='text']").first
            await textarea.clear()
            await textarea.fill(product_url)
            await page.click("button:has-text('Create Link')")
            await page.wait_for_selector("text=https://c.onlyaff.app", timeout=15000)
            link_element = page.locator("text=/https://c\\.onlyaff\\.app/\\S+/")
            affiliate_link = await link_element.inner_text()
            return affiliate_link.strip()
        finally:
            await browser.close()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("\ud83d\udd0d Analizando la imagen...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        product_id = await extract_product_id(bytes(image_bytes))
        if not product_id.isdigit():
            await update.message.reply_text(
                "No he podido encontrar el ID del producto en la imagen. "
                "Aseg\u00farate de que la captura muestre el ID num\u00e9rico del producto."
            )
            return

        logger.info(f"Product ID extracted: {product_id}")
        await update.message.reply_text(f"\u2705 Producto encontrado: `{product_id}`\n\n\u23f3 Generando link de afiliado...", parse_mode="Markdown")

        affiliate_link = await generate_affiliate_link(product_id)
        await update.message.reply_text(
            f"\ud83d\udd17 Tu link de afiliado:\n{affiliate_link}"
        )

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text(
            "Lo siento, hubo un error generando el link. Int\u00e9ntalo de nuevo."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.first_name} (@{user.username}): {user_message}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.content[0].text
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        await update.message.reply_text(
            "Lo siento, hubo un error procesando tu mensaje. Int\u00e9ntalo de nuevo."
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    if not HACOO_EMAIL or not HACOO_PASSWORD:
        raise ValueError("HACOO_EMAIL and HACOO_PASSWORD environment variables are not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
