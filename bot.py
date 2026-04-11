import os
import re
import json
import logging
import asyncio

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "").strip()
HACOO_EMAIL    = os.environ.get("HACOO_EMAIL", "").strip()
HACOO_PASSWORD = os.environ.get("HACOO_PASSWORD", "").strip()
SESSION_FILE   = "/tmp/hacoo_session.json"


# ---------------------------------------------------------------------------
# Playwright — genera el link corto de afiliado
# ---------------------------------------------------------------------------

async def _hacoo_login(page) -> None:
    from playwright.async_api import TimeoutError as PWTimeout
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)
    for sel in ['input[type="email"]', 'input[placeholder*="email" i]', 'input[type="text"]']:
        try:
            el = await page.wait_for_selector(sel, timeout=4000)
            if el:
                await el.fill(HACOO_EMAIL)
                break
        except PWTimeout:
            continue
    pw = await page.wait_for_selector('input[type="password"]', timeout=5000)
    await pw.fill(HACOO_PASSWORD)
    for sel in ['button:has-text("Sign In")', 'button:has-text("Login")', 'button[type="submit"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                break
        except Exception:
            continue
    await page.wait_for_function("!window.location.href.toLowerCase().includes('login')", timeout=20000)
    logger.info(f"[PW] Login OK")


async def generate_affiliate_link(product_id: str) -> str:
    from playwright.async_api import async_playwright

    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
    promo_url   = "https://affiliate.hacoo.app/es-ES/promotion/link"
    captured: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="en-US",
        )
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE) as f:
                    await context.add_cookies(json.load(f))
            except Exception:
                pass

        page = await context.new_page()

        async def on_response(response):
            if captured or "affiliate.hacoo.app" not in response.url or response.status != 200:
                return
            try:
                body = await response.json()
                data = body.get("data") or {}
                link = (data.get("promoLink") or data.get("shortLink") or data.get("link") or
                        body.get("promoLink") or body.get("link"))
                if link and link.startswith("http"):
                    captured.append(link)
                    logger.info(f"[PW] Link API: {link}")
            except Exception:
                pass

        page.on("response", on_response)

        try:
            await page.goto(promo_url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            if "login" in page.url.lower() or "join" in page.url.lower():
                if os.path.exists(SESSION_FILE):
                    os.remove(SESSION_FILE)
                await page.goto("https://affiliate.hacoo.app/es-ES/login", timeout=30000, wait_until="domcontentloaded")
                await _hacoo_login(page)
                await page.goto(promo_url, timeout=30000, wait_until="networkidle")
                await page.wait_for_timeout(2000)

            with open(SESSION_FILE, "w") as f:
                json.dump(await context.cookies(), f)

            # Cerrar modales
            for sel in ['button:has-text("×")', 'button:has-text("Close")', '#headlessui-portal-root button']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_timeout(400)
                except Exception:
                    continue
            await page.keyboard.press("Escape")

            # Clear
            try:
                btn = page.locator('button:has-text("Clear")').first
                if await btn.is_visible():
                    await btn.click(force=True)
                    await page.wait_for_timeout(300)
            except Exception:
                pass

            await page.wait_for_selector('textarea', timeout=10000)
            await page.locator('textarea').first.fill(product_url, force=True)
            await page.wait_for_timeout(500)

            for sel in ['button:has-text("Create Link")', 'button:has-text("Create")', 'button[type="submit"]']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible():
                        await btn.click(force=True)
                        logger.info(f"[PW] Botón: {sel}")
                        break
                except Exception:
                    continue

            for _ in range(40):
                if captured:
                    break
                try:
                    modal_link = await page.evaluate("""() => {
                        const root = document.querySelector('#headlessui-portal-root') || document.body;
                        for (const el of root.querySelectorAll('input, textarea, p, span')) {
                            const v = (el.value || el.textContent || '').trim();
                            if (v.startsWith('https://c.onlyaff')) return v;
                        }
                        return null;
                    }""")
                    if modal_link:
                        captured.append(modal_link)
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.5)

            if captured:
                return captured[0]
            raise ValueError("No se obtuvo el link corto")

        except Exception as e:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            raise
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    text = update.message.text.strip()

    # Extraer product ID del texto (número o URL de hacoo)
    product_id = ""
    m = re.search(r'/detail/(\d+)', text)
    if m:
        product_id = m.group(1)
    elif re.fullmatch(r'\d+', text):
        product_id = text

    if not product_id:
        await update.message.reply_text("Envíame el ID del producto o el link de Hacoo.")
        return

    status = await update.message.reply_text("Generando link...")
    try:
        link = await generate_affiliate_link(product_id)
        await status.edit_text(link)
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit_text(f"Error: {e}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot arrancando...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
