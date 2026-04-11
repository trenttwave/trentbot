import os
import re
import json
import base64
import logging
import asyncio
import requests

from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CHANNEL_ID     = os.environ.get("CHANNEL_ID", "").strip()
HACOO_EMAIL    = os.environ.get("HACOO_EMAIL", "").strip()
HACOO_PASSWORD = os.environ.get("HACOO_PASSWORD", "").strip()

GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
SESSION_FILE = "/tmp/hacoo_session.json"

user_states: dict = {}


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def gemini_vision(image_bytes: bytes, prompt: str) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
        {"text": prompt},
    ]}]}
    resp = requests.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=body, timeout=30)
    if resp.status_code == 429:
        try:
            msg = resp.json()["error"]["message"]
        except Exception:
            msg = resp.text[:300]
        raise Exception(f"Gemini 429: {msg}")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Playwright — link de afiliado
# ---------------------------------------------------------------------------

async def _hacoo_login(page) -> None:
    from playwright.async_api import TimeoutError as PWTimeout
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    # Rellenar email
    for sel in ['input[type="email"]', 'input[placeholder*="email" i]', 'input[type="text"]']:
        try:
            el = await page.wait_for_selector(sel, timeout=4000)
            if el:
                await el.fill(HACOO_EMAIL)
                logger.info(f"[PW] Email rellenado con: {sel}")
                break
        except PWTimeout:
            continue

    # Pulsar Enter o botón Continue/Next para pasar al paso de contraseña
    for sel in ['button:has-text("Continue")', 'button:has-text("Next")', 'button:has-text("Sign In")', 'button[type="submit"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                logger.info(f"[PW] Botón tras email: {sel}")
                break
        except Exception:
            continue
    else:
        await page.keyboard.press("Enter")

    await page.wait_for_timeout(2000)

    # Ahora rellenar contraseña
    try:
        pw = await page.wait_for_selector('input[type="password"]', timeout=8000)
        await pw.fill(HACOO_PASSWORD)
        logger.info("[PW] Contraseña rellenada")
    except PWTimeout:
        # Si no aparece campo de contraseña, intentar directamente
        logger.warning("[PW] No apareció campo de contraseña, intentando continuar")

    # Submit
    for sel in ['button:has-text("Sign In")', 'button:has-text("Login")', 'button[type="submit"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                break
        except Exception:
            continue
    else:
        await page.keyboard.press("Enter")

    await page.wait_for_function("!window.location.href.toLowerCase().includes('login')", timeout=20000)
    logger.info("[PW] Login OK")


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

            for sel in ['button:has-text("×")', 'button:has-text("Close")', '#headlessui-portal-root button']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_timeout(400)
                except Exception:
                    continue
            await page.keyboard.press("Escape")

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
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola! Envíame una captura de un producto de Hacoo.")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gemini_vision(
            base64.b64decode(
                "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
                "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
                "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
                "MjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAA"
                "AAAAAAAAAAAAAP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA"
                "/9oADAMBAAIRAxEAPwCwABmX/9k="
            ),
            "di solo 'ok'"
        )
        await update.message.reply_text("Gemini OK")
    except Exception as e:
        await update.message.reply_text(f"Gemini ERROR: {e}")


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states.pop(update.effective_user.id, None)
    await update.message.reply_text("Cancelado.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})

    # Fotos del producto para publicar
    if state.get("state") == "waiting_photos":
        state["photos"].append(update.message.photo[-1].file_id)
        await _compose_and_send(update, context)
        return

    # Captura de Hacoo — extraer ID con Gemini
    status = await update.message.reply_text("Analizando...")
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        info = gemini_vision(image_bytes,
            "Analiza esta captura de la app Hacoo. Devuelve exactamente tres líneas:\n"
            "ID: [solo el número de ID del producto]\n"
            "Precio: [precio redondeado sin decimales con símbolo €, ejemplo: 29€]\n"
            "Colores: [número total de colores/estilos disponibles]"
        ).strip()

        product_id = price = colores = ""
        for line in info.splitlines():
            if line.startswith("ID:"):
                product_id = line[3:].strip()
            elif line.startswith("Precio:"):
                price = line[7:].strip()
            elif line.startswith("Colores:"):
                m = re.search(r"\d+", line[8:])
                if m:
                    colores = m.group()

        if not product_id.isdigit():
            await status.edit_text("No encontré el ID. Asegúrate de que la captura muestre el número de producto.")
            return

        await status.edit_text(f"ID: {product_id} — Generando link...")
        link = await generate_affiliate_link(product_id)

        user_states[user_id] = {"state": "waiting_title", "link": link, "price": price, "colores": colores, "photos": []}
        await status.edit_text(f"{link}\n\nAhora envíame el título del producto.")

    except Exception as e:
        logger.error(f"Error en handle_photo: {e}")
        await status.edit_text(f"Error: {e}")


async def _compose_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    if not state.get("title") or not state.get("photos"):
        return

    link    = state["link"]
    price   = state["price"]
    title   = state["title"]
    colores = state["colores"]
    photos  = state["photos"]

    colores_text = f"\n🎨 {colores} colores disponibles" if colores else ""
    text = f"{title}\n\n💰 {price}{colores_text}\n\n🔗 {link}"

    media = [InputMediaPhoto(media=fid) for fid in photos]
    media[0] = InputMediaPhoto(media=photos[0], caption=text)

    await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
    user_states.pop(user_id, None)
    await update.message.reply_text("Publicado.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_states.get(user_id, {})

    if state.get("state") == "waiting_title":
        user_states[user_id]["title"] = text
        user_states[user_id]["state"] = "waiting_photos"
        await update.message.reply_text("Perfecto. Ahora envíame las fotos del producto.")
        return

    await update.message.reply_text("Envíame una captura de un producto de Hacoo.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("ping",     cmd_ping))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("TrentBot arrancando...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
