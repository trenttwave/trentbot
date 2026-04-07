import io
import os
import re
import json
import time
import datetime
import calendar
from zoneinfo import ZoneInfo

SPAIN_TZ = ZoneInfo("Europe/Madrid")
import base64
import hashlib
import logging
import requests
from PIL import Image
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
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
GOOGLE_VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY", "").strip()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
GEMINI_FLASH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
_SESSION_COOKIES_FILE = "/tmp/hacoo_session.json"

# Estado de conversación por usuario
# {user_id: {"link": str, "price": str, "title": str, "photos": [file_id], "state": str}}
user_states: dict = {}
media_group_buffer: dict = {}  # {media_group_id: {"photos": [], "caption": "", "user_id": int, "chat_id": int}}


def gemini_text(prompt: str) -> str:
    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    logger.info(f"Gemini text status: {resp.status_code} - {resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def gemini_vision(image_bytes: bytes, prompt: str, use_flash: bool = False) -> str:
    image_b64 = base64.b64encode(image_bytes).decode()
    url = GEMINI_FLASH_URL if use_flash else GEMINI_URL
    resp = requests.post(
        f"{url}?key={GEMINI_API_KEY}",
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
# Product image helper
# ---------------------------------------------------------------------------

def crop_product_image(image_bytes: bytes) -> bytes:
    """Recorta la mitad superior de la captura donde está la foto del producto."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    logger.info(f"Cropping image {w}x{h} to top 48%")
    cropped = img.crop((0, int(h * 0.12), w, int(h * 0.57)))
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def detect_brand(image_bytes: bytes) -> str:
    """Detecta la marca usando Google Vision Web Detection (igual que Google Lens)."""
    if GOOGLE_VISION_API_KEY:
        try:
            image_b64 = base64.b64encode(image_bytes).decode()
            resp = requests.post(
                f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}",
                json={"requests": [{"image": {"content": image_b64}, "features": [{"type": "WEB_DETECTION", "maxResults": 3}]}]},
                timeout=15,
            )
            resp.raise_for_status()
            web = resp.json()["responses"][0].get("webDetection", {})
            # bestGuessLabels es lo que Google Lens muestra como resultado principal
            for label in web.get("bestGuessLabels", []):
                if label.get("label"):
                    logger.info(f"Vision bestGuess: {label['label']}")
                    return label["label"]
            for entity in web.get("webEntities", []):
                if entity.get("score", 0) > 0.5 and entity.get("description"):
                    logger.info(f"Vision entity: {entity['description']}")
                    return entity["description"]
        except Exception as e:
            logger.warning(f"Google Vision failed: {e}")

    # Fallback: Gemini lee texto/logo directamente de la imagen
    try:
        result = gemini_vision(
            image_bytes,
            "Mira esta imagen de un producto. ¿Qué marca es? Busca logos o texto impreso. Responde SOLO el nombre de la marca, o 'Sin marca' si no la ves.",
            use_flash=True,
        )
        return result.strip()
    except Exception as e:
        logger.warning(f"Gemini brand detection failed: {e}")
        return "Sin marca"
    """Busca la imagen en Google Lens y devuelve el mejor resultado."""
    try:
        import time
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        ts = int(time.time() * 1000)
        resp = session.post(
            f"https://lens.google.com/v3/upload?hl=es&re=df&st={ts}&ep=gsbubb",
            files={"encoded_image": ("product.jpg", image_bytes, "image/jpeg")},
            timeout=20,
            allow_redirects=True,
        )
        logger.info(f"Google Lens status: {resp.status_code}, url: {resp.url}")
        text = resp.text

        # Buscar "best guess" en el JSON embebido
        patterns = [
            r'"text"\s*:\s*"([^"]{3,60})"[^}]*"type"\s*:\s*"(?:HEADER|TITLE)"',
            r'bestGuess["\s:]+([A-Za-z][^"\\]{2,50})"',
            r'"visualMatches".*?"title"\s*:\s*"([^"]{3,60})"',
            r'data-item-title="([^"]{3,60})"',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if m:
                result = m.group(1).strip()
                logger.info(f"Google Lens result: {result}")
                return result
    except Exception as e:
        logger.warning(f"Google Lens failed: {e}")
    return None


async def _get_product_image(product_id: str) -> bytes | None:
    """Descarga la imagen principal del producto de Hacoo usando Playwright."""
    from playwright.async_api import async_playwright
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(
                f"https://www.hacoo.com/en-ES/detail/{product_id}",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await page.wait_for_timeout(3000)
            img_url = await page.evaluate(
                "() => { const m = document.querySelector('meta[property=\"og:image\"]'); return m ? m.content : null; }"
            )
            await browser.close()
            if img_url:
                img_resp = requests.get(img_url, timeout=10)
                img_resp.raise_for_status()
                logger.info(f"Downloaded product image for {product_id}: {img_url}")
                return img_resp.content
    except Exception as e:
        logger.warning(f"Could not fetch product image for {product_id}: {e}")
    return None


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
                    link = data.get("promoLink") or data.get("short_url") or data.get("link") or data.get("url")
                    if link:
                        logger.info(f"promoLink API intercepted, short link: {link}")
                        link_future.set_result(link)
                    else:
                        logger.warning(f"promoLink response has no link field: {body}")
                except Exception as e:
                    logger.warning(f"Response interception error: {e}")

        page.on("response", handle_response)

        try:
            promo_url = "https://affiliate.hacoo.app/es-ES/promotion/link"
            await page.goto(promo_url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            if "login" in page.url.lower() or "join" in page.url.lower():
                # Borrar sesión caducada
                if os.path.exists(_SESSION_COOKIES_FILE):
                    os.remove(_SESSION_COOKIES_FILE)
                # Navegar a la página de login real (no /join que es registro)
                await page.goto("https://affiliate.hacoo.app/es-ES/login", timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                await _hacoo_login(page)
                await page.goto(promo_url, timeout=30000, wait_until="networkidle")
                await page.wait_for_timeout(3000)

            cookies = await context.cookies()
            with open(_SESSION_COOKIES_FILE, "w") as f:
                json.dump(cookies, f)

            # Esperar a que Vue monte el formulario (puede ser textarea)
            try:
                await page.wait_for_selector('textarea, input', timeout=10000)
            except Exception:
                pass

            # Find URL input — el campo es un textarea en esta página
            input_el = None
            for sel in [
                'textarea',
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

            await input_el.click(click_count=3)
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


async def cmd_getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"ID de este chat: `{chat.id}`", parse_mode="Markdown")


async def cmd_testgrupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_ID:
        await update.message.reply_text("⚠️ CHANNEL_ID no configurado en Railway.")
        return
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="✅ Test: el bot puede enviar mensajes al grupo.")
        await update.message.reply_text("✅ Mensaje de prueba enviado al grupo.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar al grupo: {e}")


async def cmd_enviar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    if state.get("state") not in ("editing", "waiting_photos"):
        await update.message.reply_text("No hay ningún mensaje listo para enviar.")
        return
    if not CHANNEL_ID:
        await update.message.reply_text("⚠️ CHANNEL_ID no configurado en Railway.")
        return
    try:
        photos = state.get("photos", [])
        message_text = state.get("message_text", _build_message(state))
        if photos:
            media = [InputMediaPhoto(media=pid) for pid in photos]
            media[0] = InputMediaPhoto(media=photos[0], caption=message_text)
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=message_text)
        user_states.pop(user_id, None)
        await update.message.reply_text("✅ Enviado al grupo.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        logger.info(f"[GRUPO] chat_id={update.effective_chat.id} title='{update.effective_chat.title}'")
        return
    user_id = update.effective_user.id

    state = user_states.get(user_id, {}).get("state")
    if state in ("waiting_title", "waiting_photos"):
        mg_id = update.message.media_group_id
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""

        if mg_id:
            # Foto parte de un álbum — bufferizar y procesar cuando lleguen todas
            if mg_id not in media_group_buffer:
                media_group_buffer[mg_id] = {"photos": [], "caption": "", "user_id": user_id, "chat_id": update.effective_chat.id}
                context.application.job_queue.run_once(
                    _process_media_group, 2, data=mg_id, name=mg_id
                )
            media_group_buffer[mg_id]["photos"].append(file_id)
            if caption:
                media_group_buffer[mg_id]["caption"] = caption
        else:
            # Foto individual — auto-componer directamente
            if caption and state == "waiting_title":
                user_states[user_id]["title"] = caption
                user_states[user_id]["state"] = "waiting_photos"
            user_states[user_id]["photos"].append(file_id)
            await _compose_and_send(update.effective_chat.id, user_id, context.bot)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("Analizando la imagen...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        product_info = gemini_vision(
            image_bytes,
            (
                "Analiza esta captura de pantalla de la app Hacoo. Devuelve exactamente tres líneas:\n"
                "ID: [solo el número de ID del producto]\n"
                "Precio: [precio redondeado sin decimales con símbolo €, ejemplo: 29€]\n"
                "Colores: [busca el texto 'Total X están disponibles' o 'X available' en la pantalla y devuelve ese número X; si no aparece ese texto, cuenta las miniaturas visibles en la sección Style; solo el número]"
            ),
        ).strip()

        product_id = ""
        price_raw = ""
        colores = ""
        for line in product_info.splitlines():
            if line.startswith("ID:"):
                product_id = line.replace("ID:", "").strip()
            elif line.startswith("Precio:"):
                price_raw = line.replace("Precio:", "").strip()
            elif line.startswith("Colores:"):
                colores = line.replace("Colores:", "").strip()

        if not product_id.isdigit():
            await status_msg.edit_text(
                "No encontre el ID del producto. Asegurate de que la captura muestre el ID numerico."
            )
            return

        await status_msg.edit_text(f"ID encontrado: {product_id}\nGenerando link de afiliado...")

        affiliate_link = await generate_affiliate_link(product_id)

        user_states[user_id] = {
            "state": "waiting_title",
            "link": affiliate_link,
            "price": price_raw,
            "colores": colores,
            "photos": [],
        }

        await status_msg.edit_text(
            f"{affiliate_link}\n\nAhora envíame el título del producto."
        )

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await status_msg.edit_text(f"Error: {e}")


async def _process_media_group(context) -> None:
    mg_id = context.job.data
    group = media_group_buffer.pop(mg_id, None)
    if not group:
        return
    user_id = group["user_id"]
    chat_id = group["chat_id"]
    state = user_states.get(user_id, {})
    if not state:
        return
    if state.get("state") == "waiting_title" and group["caption"]:
        user_states[user_id]["title"] = group["caption"]
        user_states[user_id]["state"] = "waiting_photos"
    for fid in group["photos"]:
        user_states[user_id]["photos"].append(fid)
    # Auto-componer sin necesidad de /listo
    await _compose_and_send(chat_id, user_id, context.bot)


async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.application.job_queue.jobs()
    scheduled = [j for j in jobs if j.name and j.name.startswith("scheduled_")]
    if not scheduled:
        await update.message.reply_text("No hay mensajes programados.")
        return
    lines = ["📅 Mensajes programados:"]
    for j in scheduled:
        when = datetime.datetime.now(SPAIN_TZ) + datetime.timedelta(seconds=max(0, (j.next_t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()))
        lines.append(f"• {when.strftime('%d/%m a las %H:%M')}")
    await update.message.reply_text("\n".join(lines))


MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS_ES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


def _build_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    now = datetime.datetime.now(SPAIN_TZ).date()
    rows = []

    # Cabecera: mes/año con flechas
    prev = datetime.date(year, month, 1) - datetime.timedelta(days=1)
    nxt = datetime.date(year, month, 28) + datetime.timedelta(days=4)
    nxt = nxt.replace(day=1)
    rows.append([
        InlineKeyboardButton("◀", callback_data=f"cal_{prev.year}-{prev.month:02d}"),
        InlineKeyboardButton(f"{MESES_ES[month]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("▶", callback_data=f"cal_{nxt.year}-{nxt.month:02d}"),
    ])

    # Días de la semana
    rows.append([InlineKeyboardButton(d, callback_data="cal_ignore") for d in DIAS_ES])

    # Días del mes
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                date = datetime.date(year, month, day)
                if date < now:
                    row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
                else:
                    label = f"{day}" if date != now else f"·{day}·"
                    row.append(InlineKeyboardButton(label, callback_data=f"cal_day_{date.isoformat()}"))
        rows.append(row)

    return InlineKeyboardMarkup(rows)


def _build_hours(date_str: str) -> InlineKeyboardMarkup:
    now = datetime.datetime.now(SPAIN_TZ)
    rows = []
    row = []
    for h in range(24):
        # Ocultar horas pasadas si es hoy
        d = datetime.date.fromisoformat(date_str)
        if d == now.date() and h <= now.hour:
            row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
        else:
            row.append(InlineKeyboardButton(f"{h:02d}", callback_data=f"cal_hour_{date_str}_{h:02d}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _build_minutes(date_str: str, hour: str) -> InlineKeyboardMarkup:
    minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    rows = []
    row = []
    for m in minutes:
        row.append(InlineKeyboardButton(f":{m:02d}", callback_data=f"cal_min_{date_str}_{hour}_{m:02d}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def cmd_programar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})
    if state.get("state") not in ("editing", "waiting_photos"):
        await update.message.reply_text("No hay ningún mensaje listo para programar.")
        return

    now = datetime.datetime.now(SPAIN_TZ)
    kb = _build_calendar(now.year, now.month)
    await update.message.reply_text("📅 Selecciona el día:", reply_markup=kb)


async def callback_calendario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "cal_ignore":
        return

    # Navegar mes
    if re.match(r"^cal_\d{4}-\d{2}$", data):
        _, ym = data.split("cal_")
        year, month = int(ym[:4]), int(ym[5:])
        kb = _build_calendar(year, month)
        await query.edit_message_reply_markup(reply_markup=kb)
        return

    # Día seleccionado → mostrar horas
    if data.startswith("cal_day_"):
        date_str = data.replace("cal_day_", "")
        d = datetime.date.fromisoformat(date_str)
        kb = _build_hours(date_str)
        await query.edit_message_text(
            f"📅 {d.strftime('%d/%m/%Y')} — Selecciona la hora:",
            reply_markup=kb,
        )
        return

    # Hora seleccionada → mostrar minutos  cal_hour_YYYY-MM-DD_HH
    if data.startswith("cal_hour_"):
        parts = data[len("cal_hour_"):].rsplit("_", 1)
        date_str, hour = parts[0], parts[1]
        d = datetime.date.fromisoformat(date_str)
        kb = _build_minutes(date_str, hour)
        await query.edit_message_text(
            f"📅 {d.strftime('%d/%m/%Y')} {hour}:__ — Selecciona los minutos:",
            reply_markup=kb,
        )
        return

    # Minutos seleccionados → programar
    if data.startswith("cal_min_"):
        # cal_min_YYYY-MM-DD_HH_MM
        parts = data[len("cal_min_"):].rsplit("_", 2)
        date_str, hour, minute = parts[0], parts[1], parts[2]
        state = user_states.get(user_id, {})
        if not state:
            await query.edit_message_text("❌ No hay ningún mensaje pendiente.")
            return

        target = datetime.datetime.strptime(f"{date_str} {hour}:{minute}", "%Y-%m-%d %H:%M").replace(tzinfo=SPAIN_TZ)
        now = datetime.datetime.now(SPAIN_TZ)
        delay = (target - now).total_seconds()
        if delay <= 0:
            await query.edit_message_text("❌ Esa hora ya ha pasado. Usa /programar de nuevo.")
            return

        context.application.job_queue.run_once(
            _send_scheduled_message,
            delay,
            data={
                "chat_id": query.message.chat_id,
                "message_text": state["message_text"],
                "photos": state.get("photos", []),
            },
            name=f"scheduled_{user_id}_{target.strftime('%d%m_%H%M')}",
        )
        user_states.pop(user_id, None)
        destino = "al grupo" if CHANNEL_ID else "⚠️ CHANNEL_ID no configurado"
        await query.edit_message_text(
            f"✅ Programado para el {target.strftime('%d/%m/%Y')} a las {hour}:{minute}\n"
            f"📤 Destino: {destino}\n\n"
            f"Usa /pendientes para ver los mensajes programados."
        )


async def _send_scheduled_message(context) -> None:
    data = context.job.data
    chat_id = data["chat_id"]
    message_text = data["message_text"]
    photos = data["photos"]
    try:
        if photos:
            media = [InputMediaPhoto(media=pid) for pid in photos]
            media[0] = InputMediaPhoto(media=photos[0], caption=message_text)
            await context.bot.send_media_group(chat_id=CHANNEL_ID or chat_id, media=media)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID or chat_id, text=message_text)
        await context.bot.send_message(chat_id=chat_id, text="✅ Mensaje enviado al grupo.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error al enviar: {e}")


def _build_message(state: dict) -> str:
    link = state.get("link", "")
    price = state.get("price", "")
    title = state.get("title", "")
    colores = state.get("colores", "")
    price_clean = price.replace(",", ".").split(".")[0].replace("€", "").strip()
    try:
        price_str = f"{int(float(price_clean))}€"
    except Exception:
        price_str = price
    colores_line = f"{colores} colores 🎨" if colores.isdigit() else "Más colores 🎨"
    return f"{title} —> {price_str}💎\n{colores_line}\n\n{link}"


async def _compose_and_send(chat_id: int, user_id: int, bot) -> None:
    state = user_states.get(user_id, {})
    photos = state.get("photos", [])
    message_text = _build_message(state)
    if photos:
        media = [InputMediaPhoto(media=pid) for pid in photos]
        media[0] = InputMediaPhoto(media=photos[0], caption=message_text)
        await bot.send_media_group(chat_id=chat_id, media=media)
    else:
        await bot.send_message(chat_id=chat_id, text=message_text)
    user_states[user_id] = {"state": "editing", "message_text": message_text, "photos": photos}
    await bot.send_message(chat_id=chat_id, text="¿Quieres modificar algo? Dímelo.\n/enviar — mandar ahora al grupo\n/programar — programar para una hora\n/cancelar — terminar")


async def cmd_listo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {})

    if state.get("state") != "waiting_photos":
        await update.message.reply_text("No hay ningún mensaje en preparación.")
        return
    await _compose_and_send(update.effective_chat.id, user_id, context.bot)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        logger.info(f"[GRUPO] chat_id={update.effective_chat.id} title='{update.effective_chat.title}'")
        return
    user_id = update.effective_user.id
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.first_name} (@{user.username}): {user_message}")

    # Si esperamos título, guardarlo
    if user_states.get(user_id, {}).get("state") == "waiting_title":
        user_states[user_id]["title"] = user_message
        user_states[user_id]["state"] = "waiting_photos"
        await update.message.reply_text("Perfecto. Ahora envíame las fotos. Cuando termines escribe /listo.")
        return

    # Si está editando el mensaje
    if user_states.get(user_id, {}).get("state") == "editing":
        current_text = user_states[user_id]["message_text"]
        photos = user_states[user_id]["photos"]
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            new_text = gemini_text(
                f"Tengo este mensaje de Telegram:\n\n{current_text}\n\n"
                f"Aplica este cambio: {user_message}\n\n"
                f"Devuelve SOLO el mensaje modificado, sin explicaciones."
            ).strip()
            user_states[user_id]["message_text"] = new_text
            if photos:
                media = [InputMediaPhoto(media=pid) for pid in photos]
                media[0] = InputMediaPhoto(media=photos[0], caption=new_text)
                await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)
            else:
                await update.message.reply_text(new_text)
        except Exception as e:
            await update.message.reply_text(f"Error al editar: {e}")
        return

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
    # job_queue está habilitado por defecto en python-telegram-bot v21
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getid", cmd_getid))
    app.add_handler(CommandHandler("testgrupo", cmd_testgrupo))
    app.add_handler(CommandHandler("enviar", cmd_enviar))
    app.add_handler(CommandHandler("listo", cmd_listo))
    app.add_handler(CommandHandler("programar", cmd_programar))
    app.add_handler(CommandHandler("pendientes", cmd_pendientes))
    app.add_handler(CommandHandler("cancelar", lambda u, c: (user_states.pop(u.effective_user.id, None), u.message.reply_text("✅ Listo."))))
    app.add_handler(CallbackQueryHandler(callback_calendario, pattern="^cal_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
