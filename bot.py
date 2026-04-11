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


# gemini-2.0-flash-lite: 30 RPM en tier gratuito (el doble que gemini-2.0-flash)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
GEMINI_FLASH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
_SESSION_COOKIES_FILE = "/tmp/hacoo_session.json"

# Estado de conversación por usuario
# {user_id: {"link": str, "price": str, "title": str, "photos": [file_id], "state": str}}
user_states: dict = {}
media_group_buffer: dict = {}  # {media_group_id: {"photos": [], "caption": "", "user_id": int, "chat_id": int}}


def _gemini_post(url: str, body: dict) -> str:
    resp = requests.post(
        f"{url}?key={GEMINI_API_KEY}",
        json=body,
        timeout=30,
    )
    model_name = url.split('/models/')[1].split(':')[0]
    logger.info(f"Gemini status ({model_name}): {resp.status_code}")
    if resp.status_code == 429:
        raise Exception("Gemini saturado (límite de peticiones). Espera un momento y vuelve a intentarlo.")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def gemini_text(prompt: str) -> str:
    return _gemini_post(GEMINI_URL, {"contents": [{"parts": [{"text": prompt}]}]})


def gemini_vision(image_bytes: bytes, prompt: str, use_flash: bool = False) -> str:
    image_b64 = base64.b64encode(image_bytes).decode()
    url = GEMINI_FLASH_URL if use_flash else GEMINI_URL
    return _gemini_post(url, {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                {"text": prompt},
            ]
        }]
    })


# ---------------------------------------------------------------------------
# Product image helpers
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Playwright-based affiliate link generation
# ---------------------------------------------------------------------------

async def _hacoo_login(page) -> None:
    from playwright.async_api import TimeoutError as PWTimeout

    logger.info(f"[PW] Login iniciado. URL: {page.url}")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    # Rellenar email
    email_filled = False
    for sel in ['input[type="email"]', 'input[name*="email" i]', 'input[placeholder*="email" i]', 'input[type="text"]']:
        try:
            el = await page.wait_for_selector(sel, timeout=4000)
            if el:
                await el.fill(HACOO_EMAIL)
                email_filled = True
                logger.info(f"[PW] Email rellenado: {sel}")
                break
        except PWTimeout:
            continue

    if not email_filled:
        raise ValueError("No se encontró el campo de email en el login")

    pw_el = await page.wait_for_selector('input[type="password"]', timeout=5000)
    await pw_el.fill(HACOO_PASSWORD)

    submitted = False
    for sel in ['button:has-text("Sign In")', 'button:has-text("Login")', 'button:has-text("Log in")', 'button[type="submit"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click()
                submitted = True
                logger.info(f"[PW] Submit clicado: {sel}")
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
        logger.info(f"[PW] Login OK. URL: {page.url}")
    except Exception:
        raise ValueError(f"Login falló. URL actual: {page.url}")


async def _dismiss_all_modals(page) -> None:
    """Cierra todos los modales/popups visibles antes de interactuar con el formulario."""
    for sel in [
        'button:has-text("×")',
        'button:has-text("✕")',
        'button:has-text("Close")',
        '[aria-label*="close" i]',
        '#headlessui-portal-root button',
        '[data-v-909a112c] button',
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible():
                logger.info(f"[PW] Cerrando modal: {sel}")
                await btn.click(force=True)
                await page.wait_for_timeout(400)
        except Exception:
            continue
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)


async def _generate_via_playwright(product_id: str) -> str | None:
    from playwright.async_api import async_playwright
    import asyncio

    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
    promo_url = "https://affiliate.hacoo.app/es-ES/promotion/link"
    captured_link: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
        )

        # Cargar cookies de sesión si existen
        if os.path.exists(_SESSION_COOKIES_FILE):
            try:
                with open(_SESSION_COOKIES_FILE) as f:
                    await context.add_cookies(json.load(f))
                logger.info("[PW] Cookies de sesión cargadas")
            except Exception as e:
                logger.warning(f"[PW] No se pudieron cargar cookies: {e}")

        page = await context.new_page()

        # Interceptar la respuesta API con el link corto.
        # Capturamos cualquier respuesta de affiliate.hacoo.app que tenga un link corto.
        async def on_response(response):
            if captured_link:
                return
            if "affiliate.hacoo.app" not in response.url:
                return
            if response.status != 200:
                return
            try:
                body = await response.json()
                data = body.get("data") or {}
                link = (
                    data.get("promoLink") or data.get("shortLink") or
                    data.get("short_url") or data.get("link") or
                    body.get("promoLink") or body.get("shortLink") or
                    body.get("short_url") or body.get("link")
                )
                if link and isinstance(link, str) and link.startswith("http"):
                    captured_link.append(link)
                    logger.info(f"[PW] Link capturado de {response.url}: {link}")
                elif "promoLink" in response.url or "link" in response.url.lower():
                    logger.warning(f"[PW] Respuesta de {response.url} sin link: {str(body)[:300]}")
            except Exception:
                pass

        page.on("response", on_response)

        try:
            logger.info(f"[PW] Navegando a {promo_url}")
            await page.goto(promo_url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            logger.info(f"[PW] URL actual: {page.url}")

            # Login si la sesión expiró
            if "login" in page.url.lower() or "join" in page.url.lower():
                logger.info("[PW] Sesión expirada, haciendo login...")
                if os.path.exists(_SESSION_COOKIES_FILE):
                    os.remove(_SESSION_COOKIES_FILE)
                await page.goto("https://affiliate.hacoo.app/es-ES/login", timeout=30000, wait_until="domcontentloaded")
                await _hacoo_login(page)
                await page.goto(promo_url, timeout=30000, wait_until="networkidle")
                await page.wait_for_timeout(2000)
                logger.info(f"[PW] URL tras login: {page.url}")

            # Guardar cookies actualizadas
            cookies = await context.cookies()
            with open(_SESSION_COOKIES_FILE, "w") as f:
                json.dump(cookies, f)
            logger.info(f"[PW] Cookies guardadas ({len(cookies)})")

            # Cerrar todos los modales abiertos antes de interactuar
            await _dismiss_all_modals(page)

            # Clicar "Clear" si está disponible (limpia la URL del producto anterior)
            for clear_sel in ['button:has-text("Clear")', 'button:has-text("Limpiar")', 'button:has-text("Reset")']:
                try:
                    btn = page.locator(clear_sel).first
                    if await btn.is_visible():
                        logger.info(f"[PW] Clear clicado: {clear_sel}")
                        await btn.click(force=True)
                        await page.wait_for_timeout(300)
                        break
                except Exception:
                    continue

            # Esperar a que el formulario esté listo
            await page.wait_for_selector('textarea, input[type="text"], input[placeholder]', timeout=10000)

            # Encontrar el textarea del formulario
            input_el = page.locator('textarea').first
            if not await input_el.is_visible():
                input_el = page.locator('input[placeholder]').first
            if not await input_el.is_visible():
                input_el = page.locator('input[type="text"]').first

            # Rellenar con fill() nativo de Playwright (fuerza la escritura sin necesitar click)
            # force=True bypasa cualquier overlay o check de accesibilidad
            await input_el.fill(product_url, force=True)
            logger.info(f"[PW] Campo rellenado con: {product_url}")
            await page.wait_for_timeout(500)

            # Clicar el botón "Create Link" (en inglés y español)
            clicked = False
            for btn_sel in [
                'button:has-text("Create Link")',
                'button:has-text("Crear enlace")',
                'button:has-text("Crear Link")',
                'button:has-text("Generate")',
                'button:has-text("Generar")',
                'button:has-text("Create")',
                'button:has-text("Crear")',
                'button:has-text("Get Link")',
                'button[type="submit"]',
                '.el-button--primary',
            ]:
                try:
                    btn = page.locator(btn_sel).first
                    if await btn.is_visible():
                        await btn.click(force=True)
                        clicked = True
                        logger.info(f"[PW] Botón clicado: {btn_sel}")
                        break
                except Exception:
                    continue

            if not clicked:
                raise ValueError("No se encontró el botón de crear link")

            # Esperar el link: API response interception + lectura directa del modal
            for i in range(40):  # hasta 20s
                if captured_link:
                    break

                # Método 2: leer el link directamente del modal "Promote Link" en el DOM
                try:
                    modal_link = await page.evaluate("""() => {
                        // El modal tiene un input/textarea con el link corto
                        const root = document.querySelector('#headlessui-portal-root')
                                  || document.querySelector('[role="dialog"]')
                                  || document.body;
                        const els = root.querySelectorAll('input, textarea, p, span, div');
                        for (const el of els) {
                            const v = (el.value || el.textContent || '').trim();
                            if (v.startsWith('https://c.onlyaff') || v.startsWith('http://c.onlyaff')) {
                                return v;
                            }
                        }
                        return null;
                    }""")
                    if modal_link:
                        captured_link.append(modal_link)
                        logger.info(f"[PW] Link leído del modal DOM: {modal_link}")
                        break
                except Exception:
                    pass

                await asyncio.sleep(0.5)

            if captured_link:
                logger.info(f"[PW] Link final: {captured_link[0]}")
                return captured_link[0]

            logger.error("[PW] Timeout: no se capturó el link de afiliado")
            return None

        except Exception as e:
            logger.error(f"[PW] Error: {e}")
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
    link = await _generate_via_playwright(product_id)
    if link:
        logger.info(f"Affiliate link: {link}")
        return link
    raise ValueError("No se pudo obtener el link corto de afiliado")


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
                "Analiza esta captura de la app Hacoo. Devuelve exactamente tres líneas:\n"
                "ID: [solo el número de ID del producto]\n"
                "Precio: [precio redondeado sin decimales con símbolo €, ejemplo: 29€]\n"
                "Colores: [si ves el texto 'Total X están disponibles' devuelve ese número; "
                "si no, cuenta todas las miniaturas de la sección Style y devuelve solo el número]"
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
                val = line.replace("Colores:", "").strip()
                if re.search(r"\d+", val):
                    colores = re.search(r"\d+", val).group()

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
        # Mensaje de error limpio sin exponer URLs ni API keys
        msg = str(e)
        if "429" in msg or "Too Many Requests" in msg or "rate limit" in msg.lower():
            await status_msg.edit_text("Gemini está saturado ahora mismo (límite de peticiones). Espera un momento y vuelve a intentarlo.")
        else:
            await status_msg.edit_text(f"Error procesando la imagen. Inténtalo de nuevo.")


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

    for i, j in enumerate(scheduled, 1):
        when = datetime.datetime.now(SPAIN_TZ) + datetime.timedelta(seconds=max(0, (j.next_t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()))
        data = j.data or {}
        message_text = data.get("message_text", "")
        photos = data.get("photos", [])
        header = f"📅 {i}. {when.strftime('%d/%m a las %H:%M')}\n\n{message_text}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Cancelar este mensaje", callback_data=f"cancel_job_{j.name}")]])
        if photos:
            media = [InputMediaPhoto(media=pid) for pid in photos]
            media[0] = InputMediaPhoto(media=photos[0], caption=header)
            await update.message.reply_media_group(media=media)
            await update.message.reply_text("↑ Este mensaje", reply_markup=kb)
        else:
            await update.message.reply_text(header, reply_markup=kb)


async def callback_cancel_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    job_name = query.data.replace("cancel_job_", "")
    jobs = context.application.job_queue.jobs()
    found = False
    for j in jobs:
        if j.name == job_name:
            j.schedule_removal()
            found = True
            break
    if found:
        await query.edit_message_text("✅ Mensaje cancelado.")
    else:
        await query.edit_message_text("❌ No se encontró el mensaje (ya fue enviado o cancelado).")


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
        d = datetime.date.fromisoformat(date_str)
        if d == now.date() and h < now.hour:
            row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
        else:
            row.append(InlineKeyboardButton(f"{h:02d}", callback_data=f"cal_hour_{date_str}_{h:02d}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    d = datetime.date.fromisoformat(date_str)
    rows.append([InlineKeyboardButton("← Cambiar día", callback_data=f"cal_{d.year}-{d.month:02d}")])
    return InlineKeyboardMarkup(rows)


def _build_minutes(date_str: str, hour: str) -> InlineKeyboardMarkup:
    now = datetime.datetime.now(SPAIN_TZ)
    d = datetime.date.fromisoformat(date_str)
    minutes = list(range(60))
    rows = []
    row = []
    for m in minutes:
        # Ocultar minutos pasados si es hoy y la hora actual
        if d == now.date() and int(hour) == now.hour and m <= now.minute:
            row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
        else:
            row.append(InlineKeyboardButton(f":{m:02d}", callback_data=f"cal_min_{date_str}_{hour}_{m:02d}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("← Cambiar hora", callback_data=f"cal_day_{date_str}")])
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
    await bot.send_message(chat_id=chat_id, text="¿Quieres modificar algo? Dímelo, usa /programar para enviarlo al grupo a una hora, o /cancelar para terminar.")


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
    app.add_handler(CommandHandler("listo", cmd_listo))
    app.add_handler(CommandHandler("programar", cmd_programar))
    app.add_handler(CommandHandler("pendientes", cmd_pendientes))
    app.add_handler(CommandHandler("cancelar", lambda u, c: (user_states.pop(u.effective_user.id, None), u.message.reply_text("✅ Listo."))))
    app.add_handler(CallbackQueryHandler(callback_calendario, pattern="^cal_"))
    app.add_handler(CallbackQueryHandler(callback_cancel_job, pattern="^cancel_job_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
