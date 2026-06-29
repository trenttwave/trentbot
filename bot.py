import os
import re
import json
import time
import asyncio
import datetime
import calendar
from zoneinfo import ZoneInfo

SPAIN_TZ = ZoneInfo("Europe/Madrid")
import base64
import logging
import requests
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
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS", "").strip()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_FALLBACK_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
_SESSION_COOKIES_FILE = "/tmp/hacoo_session.json"
_JOBS_FILE = "/tmp/scheduled_jobs.json"

# Estado de conversación por usuario
user_states: dict = {}
media_group_buffer: dict = {}

# ---------------------------------------------------------------------------
# Playwright — browser persistent entre peticions
# ---------------------------------------------------------------------------
_pw_lock: asyncio.Lock | None = None
_pw_runtime: dict = {}  # keys: playwright, browser, context


def _get_pw_lock() -> asyncio.Lock:
    global _pw_lock
    if _pw_lock is None:
        _pw_lock = asyncio.Lock()
    return _pw_lock


async def _ensure_pw_runtime():
    """Retorna (browser, context), creant-los si no existeixen o si han mort."""
    global _pw_runtime
    from playwright.async_api import async_playwright

    browser = _pw_runtime.get("browser")
    if browser:
        try:
            if browser.is_connected():
                return browser, _pw_runtime["context"]
        except Exception:
            pass

    # Netejar estat antic
    for key in ("context", "browser"):
        try:
            obj = _pw_runtime.pop(key, None)
            if obj:
                await obj.close()
        except Exception:
            pass
    try:
        pw = _pw_runtime.pop("playwright", None)
        if pw:
            await pw.stop()
    except Exception:
        pass

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
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

    _pw_runtime["playwright"] = pw
    _pw_runtime["browser"] = browser
    _pw_runtime["context"] = context
    logger.info("Playwright runtime created (browser persistent)")
    return browser, context

# ---------------------------------------------------------------------------
# Firebase / Firestore
# ---------------------------------------------------------------------------

_firestore_client = None


def _get_firestore():
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client
    if not FIREBASE_CREDENTIALS:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fb_firestore
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        if not firebase_admin._apps:
            bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip() or f"{cred_dict.get('project_id', '')}.appspot.com"
            firebase_admin.initialize_app(credentials.Certificate(cred_dict), {"storageBucket": bucket_name})
        _firestore_client = fb_firestore.client()
        return _firestore_client
    except Exception as e:
        logger.warning(f"Firebase init failed: {e}")
        return None


async def _upload_product_image(img_bytes: bytes) -> str:
    if _get_firestore() is None:
        return ""
    try:
        import uuid
        from firebase_admin import storage as fb_storage
        bucket = fb_storage.bucket()
        blob = bucket.blob(f"product_images/{uuid.uuid4().hex}.jpg")
        blob.upload_from_string(img_bytes, content_type="image/jpeg")
        blob.make_public()
        return blob.public_url
    except Exception as e:
        logger.warning(f"Firebase Storage upload failed: {e}")
        return ""


def _detect_categoria(nom: str) -> str:
    import unicodedata, re
    n = unicodedata.normalize('NFD', (nom or '').lower())
    n = ''.join(c for c in n if unicodedata.category(c) != 'Mn')
    if re.search(r'futbol|football|soccer|balon|equipacion|champions|copa|liga\b|mundial|seleccion|titular|visitante|retro shirt|camiseta retro|jersey club|kit de futbol|camiseta del|camiseta de futbol|real madrid|barcelona|barca\b|atletico de madrid|atletico madrid|psg|paris saint|manchester|man city|man united|liverpool|chelsea|arsenal|tottenham|bayern|dortmund|juventus|inter de milan|ac milan|napoli|roma\b|brasil|argentina|francia\b|alemania\b|italia\b|portugal\b|espana\b|holanda\b|inglaterra\b|croacia\b|nike futbol|adidas futbol', n): return 'Fútbol ⚽'
    if re.search(r'zapati|sneaker|zapatill|boot|bota|shoe|calzad', n): return 'Zapatos'
    if re.search(r'camiseta|tee|tshirt|polo|shirt|camisa|top\b', n): return 'Camisetas'
    if re.search(r'hoodie|sudadera|sweat|jersey|crewneck', n): return 'Sudaderas'
    if re.search(r'pantalon|jean|denim|cargo|jogger|short|bermuda|vaquero', n): return 'Pantalones'
    if re.search(r'puffer|chaqueton|parka|trench|abrigo largo|abrigo de plumas|plumifero|plumon', n): return 'Puffer/Chaquetón'
    if re.search(r'chaqueta|jacket|abrigo|coat|blazer|chaleco', n): return 'Chaquetas'
    if re.search(r'bolso|bag|mochila|tote|clutch|cartera', n): return 'Bolsos'
    if re.search(r'vestido|dress|falda|skirt', n): return 'Vestidos'
    if re.search(r'gorro|hat|cap|gorra|beanie|bucket|scrunchie', n): return 'Accesorios'
    if re.search(r'cinturon|belt|collar|pulsera|anillo|ring|joya|jewel|bufanda|scarf', n): return 'Accesorios'
    if re.search(r'auricular|airpod|earbud|earphone|headphone|altavoz|speaker|iphone|ipad|macbook|apple watch|smartwatch|airtag|cargador|charger|powerbank|electronic', n): return 'Electrónica'
    return 'Otros'

def save_to_firestore(nom: str, preu: str, colors: str, marca: str, link_afiliats: str, imatge: str, categoria: str = "", imagenes: list = None):
    db = _get_firestore()
    if not db:
        return
    try:
        from firebase_admin import firestore as fb_firestore
        db.collection("products").add({
            "nom": nom,
            "preu": preu,
            "colors": colors,
            "marca": marca,
            "link_afiliats": link_afiliats,
            "imatge": imatge,
            "imagenes": imagenes or ([imatge] if imatge else []),
            "categoria": categoria or _detect_categoria(nom),
            "data": fb_firestore.SERVER_TIMESTAMP,
        })
        logger.info("Product saved to Firestore")
    except Exception as e:
        logger.warning(f"Firestore save failed: {e}")


def _save_scheduled_job(job_name: str, target_ts: float, chat_id: int, message_text: str, photos: list):
    job = {"name": job_name, "target_ts": target_ts, "chat_id": chat_id, "message_text": message_text, "photos": photos}
    try:
        db = _get_firestore()
        if db is not None:
            db.collection("scheduled_jobs").document(job_name).set(job)
            return
    except Exception as e:
        logger.warning(f"Could not save job to Firestore: {e}")
    # Fallback local (se pierde en cada deploy, pero sirve si Firestore no está disponible)
    try:
        jobs = _load_scheduled_jobs_local()
        jobs = [j for j in jobs if j.get("name") != job_name]
        jobs.append(job)
        with open(_JOBS_FILE, "w") as f:
            json.dump(jobs, f)
    except Exception as e:
        logger.warning(f"Could not save job locally: {e}")


def _remove_scheduled_job(job_name: str):
    try:
        db = _get_firestore()
        if db is not None:
            db.collection("scheduled_jobs").document(job_name).delete()
    except Exception as e:
        logger.warning(f"Could not remove job from Firestore: {e}")
    try:
        jobs = _load_scheduled_jobs_local()
        jobs = [j for j in jobs if j.get("name") != job_name]
        with open(_JOBS_FILE, "w") as f:
            json.dump(jobs, f)
    except Exception as e:
        logger.warning(f"Could not remove job locally: {e}")


def _load_scheduled_jobs() -> list:
    try:
        db = _get_firestore()
        if db is not None:
            return [doc.to_dict() for doc in db.collection("scheduled_jobs").stream()]
    except Exception as e:
        logger.warning(f"Could not load jobs from Firestore: {e}")
    return _load_scheduled_jobs_local()


def _load_scheduled_jobs_local() -> list:
    try:
        if os.path.exists(_JOBS_FILE):
            with open(_JOBS_FILE) as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load jobs: {e}")
    return []


def _gemini_post(url: str, body: dict) -> str:
    for attempt in range(5):
        current_url = GEMINI_FALLBACK_URL if attempt >= 3 else url
        try:
            resp = requests.post(
                f"{current_url}?key={GEMINI_API_KEY}",
                json=body,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            if attempt < 4:
                time.sleep(4 * (attempt + 1))
                continue
            raise Exception("No se pudo conectar con Gemini. Inténtalo de nuevo.") from e
        logger.info(f"Gemini status ({current_url.split('/models/')[1].split(':')[0]}): {resp.status_code}")
        if resp.status_code in (429, 500, 503):
            if attempt < 4:
                wait = 4 * (attempt + 1)
                logger.warning(f"Gemini {resp.status_code}, reintentando en {wait}s...")
                time.sleep(wait)
                continue
            raise Exception("Gemini no está disponible ahora mismo (503). Espera unos segundos e inténtalo de nuevo.")
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates")
        if not candidates:
            feedback = data.get("promptFeedback", {})
            reason = feedback.get("blockReason", "sin candidatos")
            raise Exception(f"Gemini no devolvió respuesta ({reason}). Espera un momento e inténtalo de nuevo.")
        return candidates[0]["content"]["parts"][0]["text"]


def gemini_text(prompt: str) -> str:
    return _gemini_post(GEMINI_URL, {"contents": [{"parts": [{"text": prompt}]}]})


def _enrich_title(titulo: str) -> tuple[str, str, str]:
    """Devuelve (titulo_corregido, marca, categoria) usando Gemini solo con el texto."""
    try:
        resp = gemini_text(
            f"Analiza este título de producto de moda: \"{titulo}\"\n"
            "Devuelve exactamente tres líneas:\n"
            "Titulo: [título corregido en español, con mayúscula inicial, ortografía correcta]\n"
            "Marca: [nombre de la marca detectada, o vacío si no hay]\n"
            "Categoria: [una de estas opciones exactas: Zapatos, Camisetas, Sudaderas, Pantalones, Chaquetas, Bolsos, Vestidos, Accesorios, Otros]\n"
            "Solo esas tres líneas, sin explicaciones adicionales."
        ).strip()
        titulo_ok, marca_ok, cat_ok = titulo, "", ""
        for line in resp.splitlines():
            if line.startswith("Titulo:"):
                titulo_ok = line.replace("Titulo:", "").strip()
            elif line.startswith("Marca:"):
                marca_ok = line.replace("Marca:", "").strip()
            elif line.startswith("Categoria:"):
                cat_ok = line.replace("Categoria:", "").strip()
        return titulo_ok, marca_ok, cat_ok
    except Exception as e:
        logger.warning(f"_enrich_title failed: {e}")
        return titulo, "", ""


def gemini_vision(image_bytes: bytes, prompt: str) -> str:
    image_b64 = base64.b64encode(image_bytes).decode()
    return _gemini_post(GEMINI_URL, {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                {"text": prompt},
            ]
        }]
    })


def _fetch_og_image_url(product_id: str) -> str | None:
    try:
        url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        for pattern in [
            r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
            r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"',
        ]:
            m = re.search(pattern, resp.text)
            if m:
                return m.group(1)
    except Exception as e:
        logger.warning(f"og:image fetch failed: {e}")
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
    from playwright.async_api import TimeoutError as PWTimeout

    product_url = f"https://www.hacoo.pl/en-ES/detail/{product_id}"

    async with _get_pw_lock():
        browser, context = await _ensure_pw_runtime()
        page = await context.new_page()

        promo_state = {"link": None, "error": False}
        promo_ready = asyncio.Event()

        async def handle_response(response):
            if "promoLink" not in response.url:
                return
            try:
                body = await response.json()
                data = body.get("data") or {}
                link = data.get("promoLink") or data.get("short_url") or data.get("link") or data.get("url")
                if link:
                    logger.info(f"promoLink API intercepted: {link}")
                    promo_state["link"] = link
                else:
                    logger.warning(f"promoLink response has no link field: {body}")
                    promo_state["error"] = True
            except Exception as e:
                logger.warning(f"Response interception error: {e}")
                promo_state["error"] = True
            promo_ready.set()

        page.on("response", handle_response)

        try:
            promo_url = "https://affiliate.hacoo.app/es-ES/promotion/link"
            logger.info("[PW] Navegando a promo_url")
            await page.goto(promo_url, timeout=30000, wait_until="domcontentloaded")
            # Esperar que Vue Router acabi la redirecció (login o promo page)
            try:
                await page.wait_for_function(
                    "window.location.href.includes('promotion/link') || "
                    "window.location.href.toLowerCase().includes('login') || "
                    "window.location.href.toLowerCase().includes('join')",
                    timeout=5000,
                )
            except Exception:
                pass
            logger.info(f"[PW] URL tras goto: {page.url}")

            if "login" in page.url.lower() or "join" in page.url.lower():
                logger.info("[PW] Sesión expirada, haciendo login...")
                if os.path.exists(_SESSION_COOKIES_FILE):
                    os.remove(_SESSION_COOKIES_FILE)
                await context.clear_cookies()
                await page.goto("https://affiliate.hacoo.app/es-ES/login", timeout=30000, wait_until="domcontentloaded")
                await _hacoo_login(page)
                await page.goto(promo_url, timeout=30000, wait_until="domcontentloaded")
                # Esperar que Vue carregui el formulari post-login
                try:
                    await page.wait_for_function(
                        "window.location.href.includes('promotion/link')",
                        timeout=5000,
                    )
                except Exception:
                    pass
                logger.info(f"[PW] URL tras login+goto: {page.url}")

            # Guardar cookies
            cookies = await context.cookies()
            with open(_SESSION_COOKIES_FILE, "w") as f:
                json.dump(cookies, f)
            logger.info(f"[PW] Cookies guardadas ({len(cookies)})")

            # Esperar a que Vue monte el formulario
            try:
                await page.wait_for_selector('textarea, input', timeout=8000)
            except Exception:
                pass

            # Find URL input
            input_el = None
            for sel in [
                'textarea[placeholder]',
                'textarea[placeholder*="link" i]',
                'textarea[placeholder*="url" i]',
                'textarea[placeholder*="http" i]',
                'input[placeholder*="link" i]',
                'input[placeholder*="url" i]',
                'input[placeholder*="http" i]',
                'input[placeholder*="product" i]',
                'input[placeholder*="Please" i]',
                'input[placeholder*="Enter" i]',
                '.el-input__inner',
                'input[type="text"]',
                'input[type="url"]',
                'textarea',
                'input:not([type])',
            ]:
                try:
                    els = page.locator(sel)
                    count = await els.count()
                    for i in range(count):
                        el = els.nth(i)
                        if await el.is_visible():
                            val = await el.input_value()
                            if val.startswith("http") and "hacoo" not in val:
                                continue
                            logger.info(f"[PW] Found URL input selector={sel}")
                            input_el = el
                            break
                    if input_el:
                        break
                except Exception:
                    continue

            if not input_el:
                inputs = await page.query_selector_all('input')
                logger.error(f"[PW] No input found. {len(inputs)} inputs. URL: {page.url}")
                raise ValueError("Could not find URL input on promotion/link page")

            # Cerrar modals abiertos
            for close_sel in [
                'button:has-text("×")',
                'button:has-text("✕")',
                'button:has-text("Close")',
                '[aria-label*="close" i]',
                '#headlessui-portal-root button',
            ]:
                try:
                    btn = page.locator(close_sel).first
                    if await btn.is_visible():
                        await btn.click(force=True)
                except Exception:
                    continue
            await page.keyboard.press("Escape")

            # Reintentar hasta 3 veces
            for attempt in range(3):
                promo_state["link"] = None
                promo_state["error"] = False
                promo_ready.clear()

                try:
                    btn = page.locator('button:has-text("Clear")').first
                    if await btn.is_visible():
                        await btn.click(force=True)
                        await page.wait_for_timeout(100)
                except Exception:
                    pass

                await input_el.click(click_count=3)
                await input_el.fill(product_url)
                logger.info(f"[PW] Intento {attempt+1}: rellenado {product_url}")

                # Click Create Link
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

                # Esperar resposta — event-driven (API intercept) + modal DOM en paral·lel
                async def _try_modal():
                    try:
                        await page.wait_for_selector(':has-text("Promote Link")', timeout=18000)
                        await page.wait_for_timeout(500)
                        link = await page.evaluate("""() => {
                            const inputs = document.querySelectorAll('input, textarea');
                            for (const el of inputs) {
                                const v = el.value || '';
                                if (v.startsWith('http') && v.includes('onlyaff')) return v.trim();
                            }
                            const text = document.body.innerText || '';
                            for (const line of text.split('\\n')) {
                                const t = line.trim();
                                if (t.startsWith('http') && t.includes('onlyaff')) return t;
                            }
                            return null;
                        }""")
                        if link and link.startswith("http"):
                            logger.info(f"[PW] Modal link: {link}")
                            promo_state["link"] = link
                            promo_ready.set()
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.debug(f"[PW] Modal wait: {e}")

                modal_task = asyncio.create_task(_try_modal())
                try:
                    await asyncio.wait_for(promo_ready.wait(), timeout=20.0)
                except asyncio.TimeoutError:
                    pass
                finally:
                    if not modal_task.done():
                        modal_task.cancel()
                        try:
                            await modal_task
                        except (asyncio.CancelledError, Exception):
                            pass

                if promo_state["link"]:
                    logger.info(f"Playwright short link: {promo_state['link']}")
                    return promo_state["link"]

                if attempt < 2:
                    logger.warning(f"[PW] Intento {attempt+1} fallido, reintentando en 2s...")
                    await page.wait_for_timeout(2000)

            logger.error("Todos los intentos fallaron para generar el link de afiliado")
            return None

        except PWTimeout as e:
            logger.error(f"Playwright timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            if os.path.exists(_SESSION_COOKIES_FILE):
                os.remove(_SESSION_COOKIES_FILE)
            try:
                await context.clear_cookies()
            except Exception:
                pass
            return None
        finally:
            try:
                await page.close()
            except Exception:
                pass


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

        # Generar link i fetch og:image en paral·lel
        affiliate_link, image_url = await asyncio.gather(
            generate_affiliate_link(product_id),
            asyncio.to_thread(_fetch_og_image_url, product_id),
        )
        image_url = image_url or ""

        plain_fallback = f"https://www.hacoo.pl/en-ES/detail/{product_id}"
        link_is_affiliate = affiliate_link != plain_fallback

        user_states[user_id] = {
            "state": "waiting_title",
            "link": affiliate_link,
            "price": price_raw,
            "colores": colores,
            "image_url": image_url,
            "photos": [],
            "marca": "",
            "categoria": "",
        }

        if link_is_affiliate:
            await status_msg.edit_text(
                f"{affiliate_link}\n\nAhora envíame el título del producto."
            )
        else:
            await status_msg.edit_text(
                f"⚠️ No s'ha pogut generar el link d'afiliats (Playwright falló). "
                f"S'usa el link directe:\n{affiliate_link}\n\nAhora envíame el título del producto."
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


async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = _load_scheduled_jobs()
    if not jobs:
        await update.message.reply_text("No hay mensajes programados guardados.")
        return
    payload = json.dumps(jobs, ensure_ascii=False)
    await update.message.reply_text(f"📋BACKUP\n{payload}")


async def cmd_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if not text.startswith("📋BACKUP\n"):
        await update.message.reply_text("Formato incorrecto. Reenvía el mensaje de /backup.")
        return
    try:
        jobs = json.loads(text[len("📋BACKUP\n"):])
        now = datetime.datetime.now(SPAIN_TZ)
        restored = 0
        skipped = 0
        for job in jobs:
            target = datetime.datetime.fromtimestamp(job["target_ts"], tz=SPAIN_TZ)
            if target > now:
                delay = (target - now).total_seconds()
                context.application.job_queue.run_once(
                    _send_scheduled_message,
                    delay,
                    data=job,
                    name=job["name"],
                )
                _save_scheduled_job(job["name"], job["target_ts"], job["chat_id"], job["message_text"], job["photos"])
                restored += 1
            else:
                skipped += 1
        msg = f"✅ {restored} mensaje(s) reprogramado(s)."
        if skipped:
            msg += f"\n⚠️ {skipped} ya habían pasado su hora y se ignoraron."
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error al restaurar: {e}")


async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.application.job_queue.jobs()
    scheduled = [j for j in jobs if j.name and j.name.startswith("scheduled_")]
    if not scheduled:
        await update.message.reply_text("No hay mensajes programados.")
        return
    for i, j in enumerate(scheduled, 1):
        delay = (j.next_t - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        when = datetime.datetime.now(SPAIN_TZ) + datetime.timedelta(seconds=max(0, delay))
        data = j.data or {}
        message_text = data.get("message_text", "")
        photos = data.get("photos", [])
        header = f"📅 {i}. {when.strftime('%d/%m a las %H:%M')}\n\n{message_text}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Cancelar", callback_data=f"cancel_job_{j.name}")]])
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
    for j in context.application.job_queue.jobs():
        if j.name == job_name:
            j.schedule_removal()
            _remove_scheduled_job(job_name)
            await query.edit_message_text("✅ Mensaje cancelado.")
            return
    await query.edit_message_text("❌ No se encontró el mensaje (ya enviado o cancelado).")


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
        if (target - now).total_seconds() <= 0:
            await query.edit_message_text("❌ Esa hora ya ha pasado. Usa /programar de nuevo.")
            return

        if not CHANNEL_ID:
            await query.edit_message_text("❌ CHANNEL_ID no configurado.")
            return

        message_text = state.get("message_text", "")
        photos = state.get("photos", [])
        delay = (target - now).total_seconds()
        job_name = f"scheduled_{user_id}_{target.strftime('%d%m_%H%M')}_{int(now.timestamp())}"

        context.application.job_queue.run_once(
            _send_scheduled_message,
            delay,
            data={
                "chat_id": query.message.chat_id,
                "message_text": message_text,
                "photos": photos,
                "job_name": job_name,
            },
            name=job_name,
        )
        _save_scheduled_job(job_name, target.timestamp(), query.message.chat_id, message_text, photos)
        user_states.pop(user_id, None)
        destino = "al canal" if CHANNEL_ID else "⚠️ CHANNEL_ID no configurado"
        await query.edit_message_text(
            f"✅ Programado para el {target.strftime('%d/%m/%Y')} a las {hour}:{minute}\n"
            f"📤 Destino: {destino}\n\n"
            f"Usa /pendientes para ver los mensajes programados."
        )
        # Solo ahora que se ha programado de verdad, publicamos el producto en la web
        asyncio.create_task(_save_product_to_firestore(state))




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
    colores_line = f"{colores} color 🎨" if colores == "1" else (f"{colores} colores 🎨" if colores.isdigit() else "Más colores 🎨")
    return f"{title} —> {price_str}💎\n{colores_line}\n\n{link}"


async def _send_scheduled_message(context) -> None:
    data = context.job.data
    chat_id = data["chat_id"]
    message_text = data["message_text"]
    photos = data["photos"]
    _remove_scheduled_job(context.job.name)
    try:
        if photos:
            media = [InputMediaPhoto(media=pid) for pid in photos]
            media[0] = InputMediaPhoto(media=photos[0], caption=message_text)
            await context.bot.send_media_group(chat_id=CHANNEL_ID or chat_id, media=media)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID or chat_id, text=message_text)
        await context.bot.send_message(chat_id=chat_id, text="✅ Mensaje enviado al canal.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error al enviar: {e}")


async def _save_product_to_firestore(state: dict) -> None:
    """Guarda el producto en Firestore (web) — se llama solo al programar el envío."""
    try:
        photos = state.get("photos", [])
        price = state.get("price", "")
        price_clean = price.replace(",", ".").split(".")[0].replace("€", "").strip()
        try:
            preu_str = f"{int(float(price_clean))}€"
        except Exception:
            preu_str = price

        imatge = state.get("image_url", "")
        imagenes = []

        if photos:
            bot = state.get("_bot")
            for pid in photos:
                try:
                    file = await bot.get_file(pid)
                    img_bytes = bytes(await file.download_as_bytearray())
                    url = await _upload_product_image(img_bytes)
                    if url:
                        imagenes.append(url)
                except Exception as e:
                    logger.warning(f"Could not upload product image: {e}")

        if not imatge:
            imatge = imagenes[0] if imagenes else ""
        elif not imagenes:
            imagenes = [imatge]

        raw_title = state.get("title", "")
        titulo_ok, marca_ok, cat_ok = await asyncio.to_thread(_enrich_title, raw_title)
        marca_final = state.get("marca") or marca_ok

        save_to_firestore(
            nom=titulo_ok,
            preu=preu_str,
            colors=state.get("colores", ""),
            marca=marca_final,
            link_afiliats=state.get("link", ""),
            imatge=imatge,
            imagenes=imagenes,
            categoria=cat_ok or _detect_categoria(titulo_ok),
        )
        logger.info("Firestore save OK (al programar)")
    except Exception as e:
        logger.warning(f"Firestore save error (al programar): {e}")


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

    # Conservamos todos los datos del producto (título, precio, link, etc.) para
    # poder guardarlo en la web más adelante, solo si se llega a programar.
    user_states[user_id] = {**state, "state": "editing", "message_text": message_text, "photos": photos, "_bot": bot}
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
                f"Instrucción: {user_message}\n\n"
                f"REGLAS ESTRICTAS:\n"
                f"- NO cambies el título ni el precio ni el link\n"
                f"- Solo añade, mueve o modifica lo que se indica explícitamente\n"
                f"- Conserva exactamente el mismo formato y emojis del resto\n"
                f"- Siempre debe haber una línea en blanco justo antes del link de afiliado\n"
                f"- Devuelve SOLO el mensaje modificado, sin explicaciones"
            ).strip()
            user_states[user_id]["message_text"] = new_text
            if photos:
                media = [InputMediaPhoto(media=pid) for pid in photos]
                media[0] = InputMediaPhoto(media=photos[0], caption=new_text)
                await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)
            else:
                await update.message.reply_text(new_text)
            await update.message.reply_text("¿Quieres modificar algo más? Dímelo, usa /programar para enviarlo al canal a una hora, o /cancelar para terminar.")
        except Exception as e:
            await update.message.reply_text(f"Error al editar: {e}")
        return

    await update.message.reply_text("Envíame una captura de Hacoo para generar un post.")


PRODUCT_TTL_DAYS = 90


async def _delete_expired_products(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Borra de Firestore los productos publicados hace más de PRODUCT_TTL_DAYS días."""
    db = _get_firestore()
    if db is None:
        return
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=PRODUCT_TTL_DAYS)
    try:
        deleted = 0
        for doc in db.collection("products").stream():
            p = doc.to_dict()
            data_ts = p.get("data")
            if data_ts is None:
                continue
            dt = data_ts if isinstance(data_ts, datetime.datetime) else None
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            if dt < cutoff:
                doc.reference.delete()
                deleted += 1
        if deleted:
            logger.info(f"Eliminados {deleted} productos con más de {PRODUCT_TTL_DAYS} días")
    except Exception as e:
        logger.warning(f"Error al limpiar productos caducados: {e}")


async def _restore_scheduled_jobs(app):
    """Al arrancar, restaura los trabajos programados guardados en disco."""
    jobs = _load_scheduled_jobs()
    now = datetime.datetime.now(SPAIN_TZ)
    restored = 0
    for job in jobs:
        target = datetime.datetime.fromtimestamp(job["target_ts"], tz=SPAIN_TZ)
        if target > now:
            delay = (target - now).total_seconds()
            app.job_queue.run_once(
                _send_scheduled_message,
                delay,
                data=job,
                name=job["name"],
            )
            restored += 1
        else:
            _remove_scheduled_job(job["name"])
    if restored:
        logger.info(f"Restaurados {restored} trabajos programados")

    # Limpieza de productos caducados: una vez al arrancar y luego cada 24h
    app.job_queue.run_repeating(_delete_expired_products, interval=86400, first=10, name="cleanup_expired_products")

    # Precalentar Playwright en background para que el primer link sea rápido
    async def _warm_playwright():
        try:
            await _ensure_pw_runtime()
            logger.info("Playwright precalentado al arrancar")
        except Exception as e:
            logger.warning(f"Playwright warmup failed: {e}")
    asyncio.create_task(_warm_playwright())


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")

    app = Application.builder().token(BOT_TOKEN).post_init(_restore_scheduled_jobs).build()
    # job_queue está habilitado por defecto en python-telegram-bot v21
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getid", cmd_getid))
    app.add_handler(CommandHandler("listo", cmd_listo))
    app.add_handler(CommandHandler("programar", cmd_programar))
    app.add_handler(CommandHandler("pendientes", cmd_pendientes))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("restore", cmd_restore))
    app.add_handler(MessageHandler(filters.Regex(r"^📋BACKUP\n"), cmd_restore))
    app.add_handler(CommandHandler("cancelar", lambda u, c: (user_states.pop(u.effective_user.id, None), u.message.reply_text("✅ Listo."))))
    app.add_handler(CallbackQueryHandler(callback_calendario, pattern="^cal_"))
    app.add_handler(CallbackQueryHandler(callback_cancel_job, pattern="^cancel_job_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
