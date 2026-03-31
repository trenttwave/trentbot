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
    from playwright.async_api import TimeoutError as PWTimeout

    logger.info(f"Performing Hacoo affiliate login... Current URL: {page.url}")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(3000)
    logger.info(f"Login page URL after load: {page.url}")

    # Si no hay inputs visibles, el formulario está detrás de un botón/modal
    all_inputs = await page.query_selector_all('input')
    logger.info(f"Inputs on page before click: {len(all_inputs)}")
    if not all_inputs:
        # Usar page.locator() que sí soporta :has-text()
        clicked = False
        for login_trigger in [
            'a:has-text("Sign In")',
            'a:has-text("Sign in")',
            'a:has-text("Login")',
            'a:has-text("Log in")',
            'button:has-text("Sign In")',
            'button:has-text("Login")',
        ]:
            try:
                loc = page.locator(login_trigger).first
                if await loc.is_visible():
                    logger.info(f"Clicking login trigger: {login_trigger}")
                    await loc.click()
                    await page.wait_for_timeout(2000)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            logger.warning("No login trigger found, trying XPath")
            try:
                loc = page.locator('//a[contains(., "Sign")]').first
                if await loc.is_visible():
                    await loc.click()
                    await page.wait_for_timeout(2000)
            except Exception:
                pass
        all_inputs = await page.query_selector_all('input')
        logger.info(f"Inputs after login trigger click: {len(all_inputs)}")
        if not all_inputs:
            snippet = await page.evaluate("document.body ? document.body.innerHTML.substring(0, 1000) : 'no body'")
            logger.info(f"Body snippet after click: {snippet}")

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

    pw_el = await page.wait_for_selector('input[type="password"]', timeout=5000)
    await pw_el.fill(HACOO_PASSWORD)

    submitted = False
    for sel in [
        'button:has-text("Sign In")',
        'button:has-text("Sign in")',
        'button:has-text("Login")',
        'button:has-text("Log in")',
        'button[type="submit"]',
        'button:has-text("登录")',
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                submitted = True
                logger.info(f"Clicked submit button: {sel}")
                break
        except Exception:
            continue

    if not submitted:
        await pw_el.press("Enter")

    try:
        await page.wait_for_function(
            "!window.location.href.toLowerCase().includes('login') && !window.location.href.toLowerCase().includes('join')",
            timeout=20000,
        )
        logger.info(f"Login successful, redirected to: {page.url}")
    except Exception:
        raise ValueError(f"Login failed or timed out. Current URL: {page.url}")


async def _generate_via_playwright(product_id: str) -> str | None:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    import asyncio

    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
    loop = asyncio.get_event_loop()
    link_future: asyncio.Future = loop.create_future()

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

        if os.path.exists(_SESSION_COOKIES_FILE):
            try:
                with open(_SESSION_COOKIES_FILE) as f:
                    await context.add_cookies(json.load(f))
                logger.info("Restored cached Hacoo session cookies")
            except Exception as e:
                logger.warning(f"Could not restore cookies: {e}")

        page = await context.new_page()

        # Intercept promoLink API response to extract short link reliably
        async def handle_response(response):
            if "promoLink" in response.url and not link_future.done():
                try:
                    body = await response.json()
                    data = body.get("data") or {}
                    link = data.get("short_url") or data.get("link") or data.get("url")
                    if link:
                        logger.info(f"promoLink API intercepted, short link: {link}")
                        link_future.set_result(link)
                    else:
                        logger.warning(f"promoLink response has no link field: {body}")
                except Exception as e:
                    logger.warning(f"Response interception error: {e}")

        page.on("response", handle_response)

        try:
            promo_url = "https://affiliate.hacoo.app/en-ES/promotion/link"
            await page.goto(promo_url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower() or "join" in page.url.lower():
                # Borrar sesión caducada
                if os.path.exists(_SESSION_COOKIES_FILE):
                    os.remove(_SESSION_COOKIES_FILE)
                # Navegar a la página de login real (no /join que es registro)
                await page.goto("https://affiliate.hacoo.app/en-ES/login", timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                await _hacoo_login(page)
                await page.goto(promo_url, timeout=30000, wait_until="networkidle")
                await page.wait_for_timeout(3000)

            cookies = await context.cookies()
            with open(_SESSION_COOKIES_FILE, "w") as f:
                json.dump(cookies, f)

            # Esperar a que Vue monte el formulario antes de buscar inputs
            try:
                await page.wait_for_selector('input', timeout=10000)
            except Exception:
                pass

            # Find URL input — loop through visible inputs, not just first match
            input_el = None
            for sel in [
                'input[placeholder*="link" i]',
                'input[placeholder*="url" i]',
                'input[placeholder*="http" i]',
                'input[placeholder*="product" i]',
                'input[placeholder*="Please" i]',
                'input[placeholder*="Enter" i]',
                '.el-input__inner',
                'input[type="text"]',
                'input[type="url"]',
                'input:not([type])',
            ]:
                try:
                    els = page.locator(sel)
                    count = await els.count()
                    for i in range(count):
                        el = els.nth(i)
                        if await el.is_visible():
                            logger.info(f"Found URL input [{i}] with selector: {sel}")
                            input_el = el
                            break
                    if input_el:
                        break
                except Exception:
                    continue

            if not input_el:
                inputs = await page.query_selector_all('input')
                logger.error(f"No input found. {len(inputs)} inputs on page. URL: {page.url}")
                body_len = await page.evaluate("document.body ? document.body.innerHTML.length : 0")
                snippet = await page.evaluate("document.body ? document.body.innerHTML.substring(0, 2000) : 'no body'")
                logger.error(f"Promotion page HTML length: {body_len}")
                logger.error(f"Promotion page snippet: {snippet}")
                for i, inp in enumerate(inputs[:8]):
                    attrs = await inp.evaluate('el => ({type: el.type, placeholder: el.placeholder, class: el.className, visible: el.offsetParent !== null})')
                    logger.error(f"  input[{i}]: {attrs}")
                raise ValueError("Could not find URL input on promotion/link page")

            await input_el.triple_click()
            await input_el.fill(product_url)
            await page.wait_for_timeout(500)

            # Click Create Link button
            clicked = False
            for btn_sel in [
                'button:has-text("Create Link")',
                'button:has-text("Generate")',
                'button:has-text("Create")',
                'button:has-text("Get Link")',
                'button[type="submit"]',
                '.el-button--primary',
            ]:
                try:
                    btn = page.locator(btn_sel).first
                    if await btn.is_visible():
                        await btn.click()
                        clicked = True
                        logger.info(f"Clicked button: {btn_sel}")
                        break
                except Exception:
                    continue

            if not clicked:
                raise ValueError("Could not find Create Link button")

            # Wait for intercepted promoLink API response (up to 25s)
            try:
                result_link = await asyncio.wait_for(asyncio.shield(link_future), timeout=25)
                logger.info(f"Playwright short link: {result_link}")
                return result_link
            except asyncio.TimeoutError:
                logger.error("Timed out waiting for promoLink API response")
                return None

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
# Main link generation
# ---------------------------------------------------------------------------

async def generate_affiliate_link(product_id: str) -> str:
    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"

    if HACOO_EMAIL and HACOO_PASSWORD:
        try:
            link = await _generate_via_playwright(product_id)
            if link:
                logger.info(f"Affiliate link via Playwright: {link}")
                return link
        except Exception as e:
            logger.warning(f"Playwright failed: {e}")

    if HACOO_COOKIE:
        f_tracking = _parse_f_tracking(HACOO_COOKIE)
        if f_tracking:
            direct_link = f"{product_url}?f={f_tracking}"
            logger.info(f"Affiliate link via f-tracking: {direct_link}")
            return direct_link

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

        # No parse_mode to avoid Markdown issues with underscores in URLs
        reply_text = f"ID del producto: {product_id}\n\nLink de afiliado:\n{affiliate_link}"
        await status_msg.edit_text(reply_text)

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
