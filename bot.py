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
HACOO_EMAIL = os.environ.get("HACOO_EMAIL", "").strip()
HACOO_PASSWORD = os.environ.get("HACOO_PASSWORD", "").strip()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
_SESSION_COOKIES_FILE = "/tmp/hacoo_session.json"


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


# ---------------------------------------------------------------------------
# Playwright-based affiliate link generation
# ---------------------------------------------------------------------------

async def _hacoo_login(page) -> None:
    """Log in to affiliate.hacoo.app using HACOO_EMAIL and HACOO_PASSWORD."""
    from playwright.async_api import TimeoutError as PWTimeout

    logger.info("Performing Hacoo affiliate login...")
    await page.wait_for_load_state("networkidle")

    # Fill email
    email_filled = False
    for sel in [
        'input[type="email"]',
        'input[name*="email" i]',
        'input[placeholder*="email" i]',
        'input[placeholder*="Email"]',
        'input[type="text"]',
    ]:
        try:
            el = await page.wait_for_selector(sel, timeout=4000)
            if el:
                await el.fill(HACOO_EMAIL)
                email_filled = True
                logger.info(f"Email filled using selector: {sel}")
                break
        except PWTimeout:
            continue

    if not email_filled:
        raise ValueError("Could not find email input on login page")

    # Fill password
    pw_el = await page.wait_for_selector('input[type="password"]', timeout=5000)
    await pw_el.fill(HACOO_PASSWORD)

    # Submit
    submitted = False
    for sel in [
        'button[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Log in")',
        'button:has-text("Sign in")',
        'button:has-text("登录")',
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                submitted = True
                break
        except Exception:
            continue

    if not submitted:
        await pw_el.press("Enter")

    # Wait until no longer on login page
    try:
        await page.wait_for_function(
            "!window.location.href.toLowerCase().includes('login')",
            timeout=20000,
        )
        logger.info(f"Login successful, redirected to: {page.url}")
    except Exception:
        raise ValueError(f"Login failed or timed out. Current URL: {page.url}")


async def _generate_via_playwright(product_id: str) -> str | None:
    """Use a headless Chromium browser to generate an affiliate short link.

    Logs in to affiliate.hacoo.app, navigates to the promotion/link page,
    enters the product URL, clicks Create Link, and extracts the result.
    Caches the session cookies to avoid re-login on every call.
    """
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        # Restore cached session cookies
        if os.path.exists(_SESSION_COOKIES_FILE):
            try:
                with open(_SESSION_COOKIES_FILE) as f:
                    await context.add_cookies(json.load(f))
                logger.info("Restored cached Hacoo session cookies")
            except Exception as e:
                logger.warning(f"Could not restore cookies: {e}")

        page = await context.new_page()

        try:
            promo_url = "https://affiliate.hacoo.app/en-ES/promotion/link"
            await page.goto(promo_url, timeout=30000, wait_until="networkidle")

            # Re-login if redirected to login page
            if "login" in page.url.lower():
                await _hacoo_login(page)
                await page.goto(promo_url, timeout=30000, wait_until="networkidle")

            # Persist cookies after successful navigation
            cookies = await context.cookies()
            with open(_SESSION_COOKIES_FILE, "w") as f:
                json.dump(cookies, f)

            # Find URL input and fill it
            input_el = None
            for sel in [
                'input[placeholder*="link" i]',
                'input[placeholder*="url" i]',
                'input[placeholder*="http" i]',
                'input[placeholder*="product" i]',
                'input[type="text"]',
            ]:
                try:
                    input_el = await page.wait_for_selector(sel, timeout=5000)
                    if input_el:
                        logger.info(f"Found URL input with selector: {sel}")
                        break
                except PWTimeout:
                    continue

            if not input_el:
                raise ValueError("Could not find URL input on promotion/link page")

            await input_el.triple_click()
            await input_el.fill(product_url)

            # Click Create Link
            await page.click('button:has-text("Create Link")', timeout=8000)

            # Wait for the short link to appear
            await page.wait_for_selector("text=onlyaff.app", timeout=20000)

            # Extract the link
            result_link = None

            for sel in [
                'input[readonly]',
                '[class*="link-value"]',
                '[class*="promote"] input',
                '[class*="result"] input',
                '[class*="copy"] input',
            ]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        val = (
                            await el.get_attribute("value")
                            or await el.text_content()
                        )
                        if val and "onlyaff.app" in val:
                            result_link = val.strip()
                            break
                except Exception:
                    continue

            # Fallback: regex in page HTML
            if not result_link:
                html = await page.content()
                m = re.search(r'https://c\.onlyaff\.app/[A-Za-z0-9]+', html)
                if m:
                    result_link = m.group(0)

            logger.info(f"Playwright result: {result_link}")
            return result_link

        except PWTimeout as e:
            logger.error(f"Playwright timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            if os.path.exists(_SESSION_COOKIES_FILE):
                os.remove(_SESSION_COOKIES_FILE)
            return None
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# Fallback: direct URL with f-cookie affiliate tracking
# ---------------------------------------------------------------------------

def _parse_f_tracking(cookie: str) -> str | None:
    match = re.search(r'(?:^|;\s*)f=([^;]+)', cookie)
    if not match:
        return None
    f_value = match.group(1).strip()
    parts = [p for p in f_value.split('.') if not p.startswith('t_') and not p.startswith('v_')]
    return '.'.join(parts) if parts else None


# ---------------------------------------------------------------------------
# Main link generation: Playwright first, then fallbacks
# ---------------------------------------------------------------------------

async def generate_affiliate_link(product_id: str) -> str:
    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"

    # 1. Playwright (headless browser) — returns c.onlyaff.app short link
    if HACOO_EMAIL and HACOO_PASSWORD:
        try:
            link = await _generate_via_playwright(product_id)
            if link:
                logger.info(f"Affiliate link via Playwright: {link}")
                return link
        except Exception as e:
            logger.warning(f"Playwright failed: {e}")

    # 2. Direct URL with f-cookie tracking
    if HACOO_COOKIE:
        f_tracking = _parse_f_tracking(HACOO_COOKIE)
        if f_tracking:
            direct_link = f"{product_url}?f={f_tracking}"
            logger.info(f"Affiliate link via f-tracking: {direct_link}")
            return direct_link

    # 3. Plain product URL
    logger.warning("No affiliate method worked, returning plain URL")
    return product_url


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------

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

        affiliate_link = await generate_affiliate_link(product_id)

        reply_text = f"ID del producto: `{product_id}`\n\nLink de afiliado:\n{affiliate_link}"
        await status_msg.edit_text(reply_text, parse_mode="Markdown")

        if CHANNEL_ID:
            try:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=affiliate_link)
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

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
