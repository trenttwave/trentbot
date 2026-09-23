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
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()

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
            bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip() or f"{cred_dict.get('project_id', '')}.firebasestorage.app"
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
    if re.search(r'conjunto|tracksuit|(?<!pantalon )chandal|two piece|two-piece|set de\b|outfit set', n): return 'Conjuntos'
    if re.search(r'zapati|zapato|sneaker|zapatill|boot|bota|shoe|calzad|sandalia|chancla|zueco|mocasin|bailarina|\bshox\b|\bair max\b|\bair force\b|\bdunk\b|\bjordan\b|\baf1\b|\bnmd\b|\bultraboost\b|\bboost\b|\bforum\b|\bstan smith\b|\bsuperstar\b|\bclassic leather\b|\bnb\s*\d{3,4}\b|\b574\b|\b990\b|\b991\b|\b992\b|\b993\b|\b996\b|\b997\b|\b998\b|\b1080\b|\b2002r\b|\b327\b|\b530\b|\b550\b|\b9060\b|\b1906r?\b|\b860\b|\b880\b|\bfree run\b|\bpegasus\b|\bcortez\b|\bblazar\b|\bmetcon\b|\breact\b|\bwaffle\b|\bterrascape\b|\bozweego\b|\brs-x\b|\bsuede\b|\bcali\b|\bmayze\b|\bclyde\b|\bgel[-\s]|\bgt[-\s]\d|\bkayano\b|\bpuma\s*\d{3}\b|\bvomero\b|\bnocta\b|\bair tn\b|\bair plus\b|\btn\b|\bp6000\b|\bsndr\b|\buptempo\b|\bmind 001\b|\bnike mind\b|\bmoon sp\b|\bara rover\b|\btotal 90\b|\bmk2\b|\bnvr\b|\bnocta glide\b|\bhot step\b|\bsb dunk\b|\bsb colabo', n): return 'Zapatillas/Zapatos'
    if re.search(r'camiseta|tee|tshirt|polo|shirt|camisa|top\b', n): return 'Camisetas'
    if re.search(r'hoodie|sudadera|sweat|jersey|crewneck', n): return 'Sudaderas'
    if re.search(r'pantalon|jean|denim|cargo|jogger|short|bermuda|vaquero', n): return 'Pantalones'
    if re.search(r'puffer|chaqueton|parka|trench|abrigo largo|abrigo de plumas|plumifero|plumon', n): return 'Puffer/Chaquetón'
    if re.search(r'chaqueta|jacket|abrigo|coat|blazer|chaleco|cortavientos|chubasquero|windbreaker|raincoat|impermeable', n): return 'Chaquetas'
    if re.search(r'mochila|rinonera|fanny pack|fanny bag|waist bag|belt bag|backpack|cangurera|sling bag', n): return 'Mochilas/Riñoneras'
    if re.search(r'bolso|bolsa|bag|tote|clutch|cartera', n): return 'Bolsos/Bolsas'
    if re.search(r'vestido|dress|falda|skirt', n): return 'Vestidos'
    if re.search(r'gorro|hat|cap|gorra|beanie|bucket|sombrero', n): return 'Gorras/Gorros'
    if re.search(r'scrunchie', n): return 'Accesorios'
    if re.search(r'cinturon|belt|collar|pulsera|anillo|ring|joya|jewel|bufanda|scarf|reloj|(?<!apple )(?<!smart)watch', n): return 'Accesorios'
    if re.search(r'auricular|airpod|earbud|earphone|headphone|altavoz|speaker|iphone|ipad|macbook|apple watch|smartwatch|airtag|cargador|charger|powerbank|electronic|dyson|proyector|projector|microfono|microphone|\bmic\b', n): return 'Electrónica'
    if re.search(r'maquillaje|makeup|make up|labial|lipstick|gloss|pintalabios|base de maquillaje|foundation|corrector|concealer|rimel|rimmel|mascara de pestanas|sombra de ojos|eyeshadow|delineador|eyeliner|colorete|blush|bronceador|bronzer|iluminador|highlighter|polvos compactos|prebase|primer|paleta de maquillaje|brocha de maquillaje|beauty blender|cosmetic', n): return 'Maquillaje 💄'
    if re.search(r'birkenstock|golden goose|\bhoka\b|onitsuka|mizuno|saucony|\basics\b|\bautry\b|yeezy|\bveja\b|\bcrocs\b|new balance|\bvans\b|\breebok\b|salomon|dr martens|\bmartens\b|\bconverse\b|havaianas|\bugg\b|on cloud|adidas spezial|adidas samba|adidas gazelle|adidas campus', n): return 'Zapatillas/Zapatos'
    return 'Otros'

def save_to_firestore(nom: str, preu: str, colors: str, marca: str, link_afiliats: str, imatge: str, categoria: str = "", imagenes: list = None, fuente: str = "Hacoo"):
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
            "fuente": fuente,
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
            "Categoria: [una de estas opciones exactas: Zapatillas/Zapatos, Camisetas, Sudaderas, Pantalones, Chaquetas, Conjuntos, Bolsos/Bolsas, Mochilas/Riñoneras, Gorras/Gorros, Vestidos, Accesorios, Otros]\n"
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
            link = await asyncio.wait_for(_generate_via_playwright(product_id), timeout=90)
            if link:
                logger.info(f"Affiliate link via Playwright: {link}")
                return link
        except asyncio.TimeoutError:
            logger.warning("Playwright timeout (45s), falling back")
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

    # Si está en modo newsletter, procesar foto
    nl_state = user_states.get(user_id, {}).get("state", "")
    if nl_state.endswith("_waiting_name_photo"):
        # Foto para el producto de captura directa Hacoo
        section = user_states[user_id].get("newsletter_section", "zapatillas")
        file_id = update.message.photo[-1].file_id
        user_states[user_id].setdefault("nl_direct_photos", []).append(file_id)
        # Si la foto tiene caption, usarlo como nombre automáticamente
        caption = update.message.caption or ""
        if caption and not user_states[user_id].get("nl_direct_name"):
            user_states[user_id]["nl_direct_name"] = _clean_product_name(caption.splitlines()[0])
        nombre = user_states[user_id].get("nl_direct_name", "")
        if nombre:
            await _nl_save_direct_hacoo(update.message.chat.id, user_id, section, context.bot)
        else:
            await update.message.reply_text("Foto guardada. Ahora dime el nombre del producto.")
        return
    if nl_state.startswith("newsletter_") and nl_state != "newsletter_confirm":
        section = user_states[user_id].get("newsletter_section", "zapatillas")
        await _handle_newsletter_photo(update, context, user_id, section)
        return

    # Detectar mensaje de Yepexpress reenviado con foto
    caption = update.message.caption or ""
    if "(yepex)" in caption.lower():
        file_id = update.message.photo[-1].file_id
        imatge = ""
        try:
            file = await context.bot.get_file(file_id)
            img_bytes = bytes(await file.download_as_bytearray())
            imatge = await _upload_product_image(img_bytes) or ""
        except Exception as e:
            logger.warning(f"Yepexpress photo upload error: {e}")
        await _handle_yepexpress_message(update, context, caption, imatge=imatge)
        return

    state = user_states.get(user_id, {}).get("state")

    # ── Flujo canal externo: el usuario manda la captura de Hacoo ──
    if state == "waiting_hacoo_for_channel":
        await _handle_channel_hacoo_photo(update, context, user_id)
        return

    if state in ("waiting_title", "waiting_photos"):
        mg_id = update.message.media_group_id
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""

        if mg_id:
            if mg_id not in media_group_buffer:
                media_group_buffer[mg_id] = {"photos": [], "caption": "", "user_id": user_id, "chat_id": update.effective_chat.id}
                context.application.job_queue.run_once(
                    _process_media_group, 2, data=mg_id, name=mg_id
                )
            media_group_buffer[mg_id]["photos"].append(file_id)
            if caption:
                media_group_buffer[mg_id]["caption"] = caption
        else:
            if caption and state == "waiting_title":
                user_states[user_id]["title"] = caption
                user_states[user_id]["state"] = "waiting_photos"
            user_states[user_id]["photos"].append(file_id)
            await _compose_and_send(update.effective_chat.id, user_id, context.bot)
        return

    # Encolar el file_id inmediatamente (antes de descargar) para preservar el orden de envío
    chat_id = update.effective_chat.id
    file_id = update.message.photo[-1].file_id
    _hacoo_queue.setdefault(user_id, []).append({"file_id": file_id, "chat_id": chat_id})

    if user_id not in _hacoo_active:
        _hacoo_active.add(user_id)
        context.application.job_queue.run_once(
            _process_hacoo_queue_job, 0.1,
            data={"user_id": user_id},
            name=f"hacooqueue_{user_id}",
        )


async def _process_hacoo_queue_job(context: ContextTypes.DEFAULT_TYPE):
    """Procesa capturas de Hacoo en orden, una a una por usuario."""
    user_id = context.job.data["user_id"]
    queue = _hacoo_queue.get(user_id, [])
    if not queue:
        _hacoo_active.discard(user_id)
        return

    item = queue.pop(0)
    file_id = item["file_id"]
    chat_id = item["chat_id"]
    bot = context.bot

    status_msg = await bot.send_message(chat_id=chat_id, text="Analizando la imagen...")
    await bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        tg_file = await bot.get_file(file_id)
        image_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception as e:
        logger.error(f"Error descargando captura Hacoo: {e}")
        await status_msg.edit_text("⚠️ No pude descargar la imagen. Inténtalo de nuevo.")
        # Continuar con el siguiente
        if _hacoo_queue.get(user_id):
            context.application.job_queue.run_once(_process_hacoo_queue_job, 0.1, data={"user_id": user_id}, name=f"hacooqueue_{user_id}_{len(_hacoo_queue[user_id])}")
        else:
            _hacoo_active.discard(user_id)
        return

    try:
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
                "No encontré el ID del producto. Asegúrate de que la captura muestre el ID numérico."
            )
        else:
            await status_msg.edit_text(f"ID encontrado: {product_id}\nGenerando link de afiliado...")

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
                await status_msg.edit_text(f"{affiliate_link}\n\nAhora envíame el título del producto.")
            else:
                await status_msg.edit_text(
                    f"⚠️ No se pudo generar el link de afiliados (Playwright falló). "
                    f"Se usa el link directo:\n{affiliate_link}\n\nAhora envíame el título del producto."
                )

    except Exception as e:
        logger.error(f"Error procesando captura Hacoo: {e}")
        await status_msg.edit_text(f"Error: {e}")

    # Procesar el siguiente si hay más en cola
    if _hacoo_queue.get(user_id):
        context.application.job_queue.run_once(
            _process_hacoo_queue_job, 0.1,
            data={"user_id": user_id},
            name=f"hacooqueue_{user_id}_{len(_hacoo_queue[user_id])}",
        )
    else:
        _hacoo_active.discard(user_id)


async def _handle_channel_hacoo_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Procesa la captura de Hacoo cuando el usuario está en flujo de canal externo."""
    state = user_states.get(user_id, {})
    channel_key = state.get("channel_key")
    pending = _pending_channel_msgs.get(channel_key)
    if not pending:
        await update.message.reply_text("❌ El producto del canal ya no está disponible. Empieza de nuevo.")
        user_states.pop(user_id, None)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("Analizando la captura de Hacoo...")

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
            await status_msg.edit_text("No encontré el ID del producto. Envía otra captura.")
            return

        await status_msg.edit_text(f"ID: {product_id} ✓\nGenerando link de afiliado...")

        affiliate_link, image_url = await asyncio.gather(
            generate_affiliate_link(product_id),
            asyncio.to_thread(_fetch_og_image_url, product_id),
        )

        # Guardar affiliate link para esta URL
        pending_urls = state.get("pending_urls", [])
        url_index = state.get("url_index", 0)
        url_affiliate_map = state.get("url_affiliate_map", {})

        if pending_urls and url_index < len(pending_urls):
            url_affiliate_map[pending_urls[url_index]] = affiliate_link
            url_index += 1
            user_states[user_id]["url_affiliate_map"] = url_affiliate_map
            user_states[user_id]["url_index"] = url_index

        # ¿Quedan más URLs por procesar?
        if url_index < len(pending_urls):
            user_states[user_id]["state"] = "waiting_hacoo_for_channel"
            remaining = len(pending_urls) - url_index
            await status_msg.edit_text(
                f"✅ Link {url_index}/{len(pending_urls)} generado. "
                f"Ahora envíame la captura de Hacoo del siguiente ({url_index + 1}/{len(pending_urls)})."
            )
            return

        # Todos los links procesados → construir texto final
        original_text = pending["original_text"]
        url_pattern = r'https?://\S+'
        DISCOUNT_LINE = "🎁 Código descuento 14% en tu primer pedido: *TRENT14*\n"

        if url_affiliate_map:
            # Reemplazar cada URL original por su affiliate link
            working_text = original_text
            for orig_url, aff_url in url_affiliate_map.items():
                working_text = working_text.replace(orig_url, aff_url)
            # Si ya tiene 🔗 → insertar descuento antes del bloque de links (label + 🔗)
            if "🔗" in working_text:
                lines = working_text.split('\n')
                first_link_idx = next((i for i, l in enumerate(lines) if '🔗' in l), -1)
                if first_link_idx > 0:
                    # Si la línea anterior al 🔗 es un label (no vacía), incluirla en el bloque
                    label_idx = first_link_idx - 1 if lines[first_link_idx - 1].strip() else first_link_idx
                    pre = '\n'.join(lines[:label_idx]).rstrip()
                    post = '\n'.join(lines[label_idx:])
                    final_text = f"{pre}\n\n{DISCOUNT_LINE}\n{post}"
                else:
                    final_text = f"{DISCOUNT_LINE}\n{working_text}"
            else:
                # Quitar URLs sueltas y poner todo abajo con 🔗
                # Construir bloque de links
                links_block = "\n".join(f"🔗 {aff}" for aff in url_affiliate_map.values())
                clean_text = re.sub(url_pattern, "", original_text).strip()
                # Limpiar líneas vacías extra
                clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()
                final_text = f"{clean_text}\n\n{DISCOUNT_LINE}\n{links_block}" if clean_text else f"{DISCOUNT_LINE}\n{links_block}"
        else:
            final_text = f"{original_text}\n\n{DISCOUNT_LINE}\n🔗 {affiliate_link}" if original_text else f"{DISCOUNT_LINE}\n🔗 {affiliate_link}"

        user_states[user_id].update({
            "state": "channel_editing",
            "link": affiliate_link,
            "price": price_raw,
            "colores": colores,
            "image_url": image_url or "",
            "final_text": final_text,
            "original_text": original_text,
        })

        # Mostrar preview con las fotos del canal + texto modificado
        photos_bytes = pending["photo_bytes_list"]
        if len(photos_bytes) == 1:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photos_bytes[0],
                caption=f"📋 *Preview del post:*\n\n{final_text}",
                parse_mode="Markdown",
            )
        else:
            from telegram import InputMediaPhoto as IMP
            media = [IMP(media=b) for b in photos_bytes]
            media[0] = IMP(media=photos_bytes[0], caption=f"📋 *Preview del post:*\n\n{final_text}", parse_mode="Markdown")
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📤 Publicar ahora", callback_data=f"chpub_now_{channel_key}"),
            InlineKeyboardButton("🕐 Programar", callback_data=f"chpub_sched_{channel_key}"),
            InlineKeyboardButton("❌ Cancelar", callback_data=f"chpub_cancel_{channel_key}"),
        ]])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="¿Qué quieres hacer con este post?",
            reply_markup=kb,
        )

    except Exception as e:
        logger.error(f"Error en flujo canal externo: {e}")
        await status_msg.edit_text(f"Error: {e}")


async def callback_channel_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestiona publicar ahora / programar / cancelar para posts del canal externo."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("chpub_cancel_"):
        key = data.replace("chpub_cancel_", "")
        _pending_channel_msgs.pop(key, None)
        user_states.pop(user_id, None)
        await query.edit_message_text("❌ Publicación cancelada.")
        await _show_next_from_queue(user_id, query.message.chat.id, context.bot)
        return

    if data.startswith("chpub_now_"):
        key = data.replace("chpub_now_", "")
        state = user_states.get(user_id, {})
        pending = _pending_channel_msgs.get(key)
        if not pending or not state:
            await query.edit_message_text("❌ Ya no hay datos disponibles.")
            return

        final_text = state.get("final_text", "")
        photos_bytes = pending["photo_bytes_list"]

        try:
            if len(photos_bytes) == 1:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photos_bytes[0],
                    caption=final_text,
                    parse_mode="Markdown",
                )
            else:
                from telegram import InputMediaPhoto as IMP
                media = [IMP(media=b) for b in photos_bytes]
                media[0] = IMP(media=photos_bytes[0], caption=final_text, parse_mode="Markdown")
                await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)

            _pending_channel_msgs.pop(key, None)
            user_states.pop(user_id, None)
            await query.edit_message_text("✅ Publicado en el canal.")
            await _show_next_from_queue(user_id, query.message.chat.id, context.bot)
        except Exception as e:
            await query.edit_message_text(f"❌ Error al publicar: {e}")
        return

    if data.startswith("chpub_sched_"):
        # Reusar el calendario existente
        state = user_states.get(user_id, {})
        if not state:
            await query.edit_message_text("❌ No hay datos disponibles.")
            return
        # Marcar que estamos en modo programar para canal
        user_states[user_id]["state"] = "channel_scheduling"
        now = datetime.datetime.now(SPAIN_TZ)
        kb = _build_calendar(now.year, now.month)
        await query.edit_message_text("📅 Selecciona el día:", reply_markup=kb)



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

        delay = (target - now).total_seconds()
        job_name = f"scheduled_{user_id}_{target.strftime('%d%m_%H%M')}_{int(now.timestamp())}"

        # ── Flujo canal externo programado ──
        if state.get("state") == "channel_scheduling":
            channel_key = state.get("channel_key")
            pending = _pending_channel_msgs.get(channel_key, {})
            final_text = state.get("final_text", "")
            photos_bytes = pending.get("photo_bytes_list", [])

            context.application.job_queue.run_once(
                _send_channel_scheduled,
                delay,
                data={
                    "chat_id": query.message.chat_id,
                    "final_text": final_text,
                    "photos_bytes": photos_bytes,
                    "channel_key": channel_key,
                    "job_name": job_name,
                    "user_id": user_id,
                },
                name=job_name,
            )
            _pending_channel_msgs.pop(channel_key, None)
            user_states.pop(user_id, None)
            await query.edit_message_text(
                f"✅ Programado para el {target.strftime('%d/%m/%Y')} a las {hour}:{minute}\n"
                f"📤 Destino: canal\n\nUsa /pendientes para ver los mensajes programados."
            )
            return

        # ── Flujo normal ──
        message_text = state.get("message_text", "")
        photos = state.get("photos", [])

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
    discount = "🎁 Código descuento 14% en tu primer pedido: *TRENT14*\n"
    return f"{title} —> {price_str}💎\n{colores_line}\n\n{discount}\n🔗 {link}"


async def _send_scheduled_message(context) -> None:
    data = context.job.data
    chat_id = data["chat_id"]
    message_text = data["message_text"]
    photos = data["photos"]
    _remove_scheduled_job(context.job.name)
    try:
        if photos:
            media = [InputMediaPhoto(media=pid) for pid in photos]
            media[0] = InputMediaPhoto(media=photos[0], caption=message_text, parse_mode="Markdown")
            await context.bot.send_media_group(chat_id=CHANNEL_ID or chat_id, media=media)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID or chat_id, text=message_text, parse_mode="Markdown")
        await context.bot.send_message(chat_id=chat_id, text="✅ Mensaje enviado al canal.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error al enviar: {e}")


async def _send_channel_scheduled(context) -> None:
    """Envía al canal un post programado proveniente del flujo de canal externo."""
    data = context.job.data
    chat_id = data["chat_id"]
    final_text = data["final_text"]
    photos_bytes = data.get("photos_bytes", [])
    try:
        if len(photos_bytes) == 1:
            await context.bot.send_photo(chat_id=CHANNEL_ID or chat_id, photo=photos_bytes[0], caption=final_text, parse_mode="Markdown")
        elif photos_bytes:
            from telegram import InputMediaPhoto as IMP
            media = [IMP(media=b) for b in photos_bytes]
            media[0] = IMP(media=photos_bytes[0], caption=final_text, parse_mode="Markdown")
            await context.bot.send_media_group(chat_id=CHANNEL_ID or chat_id, media=media)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID or chat_id, text=final_text, parse_mode="Markdown")
        user_id = data.get("user_id", 0)
        await context.bot.send_message(chat_id=chat_id, text="✅ Mensaje del canal enviado.")
        if user_id:
            await _show_next_from_queue(user_id, chat_id, context.bot)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error al enviar: {e}")



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


async def _handle_yepexpress_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, imatge: str = "") -> None:
    """Parsea un mensaje de Yepexpress y lo guarda en Firestore."""
    try:
        # Formato: "Nike Shox r4 (yepex) —> 35€💎\nMás colores 🎨\nhttps://..."
        lines = text.strip().splitlines()

        # Línea 1: nombre y precio
        first_line = lines[0] if lines else ""
        # Extraer precio: busca "—> Xeuro" o "-> Xeuro"
        price_match = re.search(r'[—\-]>\s*([\d,.]+)\s*€', first_line)
        preu = f"{price_match.group(1)}€" if price_match else ""

        # Nombre: todo antes de "(yepex)" y del "—>"
        name_raw = re.split(r'\(yepex\)', first_line, flags=re.IGNORECASE)[0]
        name_raw = re.split(r'[—\-]>', name_raw)[0].strip()
        nom = name_raw.strip()

        # Colores: buscar línea con "colores" o "🎨"
        colors = ""
        for line in lines[1:]:
            if "color" in line.lower() or "🎨" in line:
                m = re.search(r'(\d+)', line)
                colors = f"{m.group(1)} colores" if m else ""
                break

        # Link: buscar URL en el texto
        link = ""
        for line in lines:
            url_match = re.search(r'https?://\S+', line)
            if url_match:
                link = url_match.group(0)
                break

        if not nom or not link:
            await update.message.reply_text("❌ No pude parsear el mensaje. Asegúrate de que tiene el formato correcto con (yepex) y el link.")
            return

        # Detectar marca desde el nombre
        marca = _enrich_title(nom)[1] if nom else ""
        categoria = _detect_categoria(nom)

        save_to_firestore(
            nom=nom,
            preu=preu,
            colors=colors,
            marca=marca,
            link_afiliats=link,
            imatge=imatge,
            imagenes=[imatge] if imatge else [],
            categoria=categoria,
            fuente="Yepexpress",
        )

        await update.message.reply_text(
            f"✅ Producto Yepexpress guardado en la web:\n\n"
            f"*{nom}*\n"
            f"💎 {preu}\n"
            f"🔗 {link}\n"
            f"📂 {categoria}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Yepexpress parse error: {e}")
        await update.message.reply_text(f"❌ Error al procesar el producto Yepexpress: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        logger.info(f"[GRUPO] chat_id={update.effective_chat.id} title='{update.effective_chat.title}'")
        return
    user_id = update.effective_user.id
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.first_name} (@{user.username}): {user_message}")

    # Si esperamos link de Yepex para canal externo
    if user_states.get(user_id, {}).get("state") == "waiting_yepex_url_for_channel":
        yepex_url = re.search(r'https?://\S+', user_message)
        if not yepex_url:
            await update.message.reply_text("⚠️ No he detectado ningún link. Envíame la URL del producto.")
            return
        yepex_link = yepex_url.group(0)
        state = user_states.get(user_id, {})
        channel_key = state.get("channel_key")
        pending = _pending_channel_msgs.get(channel_key)
        if not pending:
            await update.message.reply_text("❌ El producto ya no está disponible.")
            user_states.pop(user_id, None)
            return

        original_text = pending["original_text"]
        DISCOUNT_LINE = "🎁 Código descuento 14% en tu primer pedido: *TRENT14*\n"
        url_pattern = r'https?://\S+'

        # Reemplazar link original por el Yepex link proporcionado
        if "🔗" in original_text:
            lines = original_text.split('\n')
            first_link_idx = next((i for i, l in enumerate(lines) if '🔗' in l), -1)
            if first_link_idx > 0:
                label_idx = first_link_idx - 1 if lines[first_link_idx - 1].strip() else first_link_idx
                pre = '\n'.join(lines[:label_idx]).rstrip()
                post = re.sub(url_pattern, yepex_link, '\n'.join(lines[label_idx:]), count=1)
                final_text = f"{pre}\n\n{DISCOUNT_LINE}\n{post}"
            else:
                final_text = f"{DISCOUNT_LINE}\n{re.sub(url_pattern, yepex_link, original_text, count=1)}"
        else:
            clean_text = re.sub(url_pattern, "", original_text).strip()
            final_text = f"{clean_text}\n\n{DISCOUNT_LINE}\n🔗 {yepex_link}" if clean_text else f"{DISCOUNT_LINE}\n🔗 {yepex_link}"

        user_states[user_id].update({
            "state": "channel_editing",
            "link": yepex_link,
            "final_text": final_text,
            "original_text": original_text,
        })

        photos_bytes = pending["photo_bytes_list"]
        if len(photos_bytes) == 1:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photos_bytes[0],
                caption=f"📋 *Preview del post:*\n\n{final_text}",
                parse_mode="Markdown",
            )
        else:
            from telegram import InputMediaPhoto as IMP
            media = [IMP(media=b) for b in photos_bytes]
            media[0] = IMP(media=photos_bytes[0], caption=f"📋 *Preview del post:*\n\n{final_text}", parse_mode="Markdown")
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📤 Publicar ahora", callback_data=f"chpub_now_{channel_key}"),
            InlineKeyboardButton("🕐 Programar", callback_data=f"chpub_sched_{channel_key}"),
            InlineKeyboardButton("❌ Cancelar", callback_data=f"chpub_cancel_{channel_key}"),
        ]])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="¿Qué quieres hacer con este post?",
            reply_markup=kb,
        )
        return

    # Si esperamos título, guardarlo
    if user_states.get(user_id, {}).get("state") == "waiting_title":
        user_states[user_id]["title"] = user_message
        user_states[user_id]["state"] = "waiting_photos"
        await update.message.reply_text("Perfecto. Ahora envíame las fotos. Cuando termines escribe /listo.")
        return

    # Si está en modo newsletter esperando captura de Hacoo y el usuario envía un link directo (Yepex)
    nl_state = user_states.get(user_id, {}).get("state", "")
    if nl_state.endswith("_waiting_hacoo") and user_states[user_id].get("nl_source") == "other":
        url_match = re.search(r'https?://\S+', user_message)
        if url_match:
            section = user_states[user_id].get("newsletter_section", "zapatillas")
            section_name = _NEWSLETTER_SECTIONS.get(section, section)
            affiliate_link = url_match.group(0).rstrip(".,)")
            pending_urls = user_states[user_id].get("nl_pending_urls", [])
            url_index = user_states[user_id].get("nl_url_index", 0)
            affiliate_map = user_states[user_id].get("nl_affiliate_map", {})
            current_url = pending_urls[url_index] if url_index < len(pending_urls) else None
            if current_url:
                nl_names = user_states[user_id].get("nl_names", [])
                saved_name = _clean_product_name(nl_names[url_index]) if url_index < len(nl_names) else ""
                nl_photo_ids = user_states[user_id].get("nl_photo_file_ids", [])
                saved_photo = nl_photo_ids[url_index] if url_index < len(nl_photo_ids) else ""
                affiliate_map[current_url] = {"link": affiliate_link, "image_url": saved_photo, "name": saved_name or "Producto", "price": ""}
                user_states[user_id]["nl_affiliate_map"] = affiliate_map
                url_index += 1
                user_states[user_id]["nl_url_index"] = url_index
                if url_index < len(pending_urls):
                    next_name = nl_names[url_index] if url_index < len(nl_names) else f"producto {url_index+1}"
                    original_text = user_states[user_id].get("nl_original_text", "")
                    next_is_yepex = bool(re.search(r'yepex|yepexpress', original_text, re.IGNORECASE))
                    if next_is_yepex:
                        await update.message.reply_text(
                            f"✅ Link {url_index}/{len(pending_urls)} guardado.\n"
                            f"Envíame tu link de afiliado YepExpress de '{next_name}' ({url_index+1}/{len(pending_urls)})."
                        )
                    else:
                        await update.message.reply_text(
                            f"✅ Link {url_index}/{len(pending_urls)} guardado.\n"
                            f"Envíame la captura de Hacoo de '{next_name}' ({url_index+1}/{len(pending_urls)}) o el link directo si es Yepex."
                        )
                else:
                    await _nl_save_all(update.message.chat.id, user_id, section, affiliate_map, context.bot)
            return

    # Si está en modo waiting_name_photo (captura directa Hacoo: esperando nombre)
    if nl_state.endswith("_waiting_name_photo"):
        section = user_states[user_id].get("newsletter_section", "zapatillas")
        section_name = _NEWSLETTER_SECTIONS.get(section, section)
        user_states[user_id]["nl_direct_name"] = _clean_product_name(user_message.strip())
        photos = user_states[user_id].get("nl_direct_photos", [])
        if photos:
            # Ya tenemos fotos → guardar
            await _nl_save_direct_hacoo(update.message.chat.id, user_id, section, context.bot)
        else:
            await update.message.reply_text("✅ Nombre guardado. Ahora envíame la foto (o fotos) del producto. Cuando termines escribe /listo_nl.")
        return

    # Si está en modo newsletter (añadiendo links de texto)
    if nl_state.startswith("newsletter_") and nl_state != "newsletter_confirm":
        section = user_states[user_id].get("newsletter_section", "zapatillas")
        await _handle_newsletter_links(update, context, user_id, section)
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

    # Detectar mensaje de Yepexpress con tag (yepex)
    if "(yepex)" in user_message.lower():
        await _handle_yepexpress_message(update, context, user_message)
        return

    await update.message.reply_text("Envíame una captura de Hacoo para generar un post.")


TELETHON_API_ID = os.environ.get("TELETHON_API_ID", "").strip()
TELETHON_API_HASH = os.environ.get("TELETHON_API_HASH", "").strip()
TELETHON_SESSION = os.environ.get("TELETHON_SESSION", "").strip()  # Sesión serializada en base64
WATCH_CHANNEL = os.environ.get("WATCH_CHANNEL", "").strip()  # Username o ID del canal a escuchar
OWNER_ID = int(os.environ.get("OWNER_ID", "0").strip())  # Tu Telegram user ID

# Almacén temporal de mensajes pendientes de canal externo
# clave: callback_data key → dict con info del mensaje
_pending_channel_msgs: dict = {}

# Cola de mensajes reenviados por usuario (procesamiento uno a uno)
_fwd_queue: dict = {}   # user_id → [{"photo_bytes_list": [...], "original_text": "..."}, ...]
_fwd_active: set = set()  # user_ids con un flujo activo en curso

# Cola FIFO de envío del canal Telethon (garantiza orden de llegada al owner)
_telethon_send_q = None         # asyncio.Queue, inicializada en _start_telethon_listener

# Cola de capturas Hacoo (flujo normal) para mantener el orden de envío
_hacoo_queue: dict = {}   # user_id → [{"image_bytes": bytes, "chat_id": int}, ...]
_hacoo_active: set = set()  # user_ids con procesamiento en curso

# ---------------------------------------------------------------------------
# Telethon — escucha canal externo
# ---------------------------------------------------------------------------

def _get_telethon_session():
    """Devuelve un StringSession desde la variable de entorno."""
    from telethon.sessions import StringSession
    return StringSession(TELETHON_SESSION) if TELETHON_SESSION else StringSession()


async def _start_telethon_listener(ptb_app):
    """Arranca el cliente Telethon y escucha mensajes del canal externo."""
    if not TELETHON_API_ID or not TELETHON_API_HASH or not WATCH_CHANNEL or not OWNER_ID:
        logger.warning("Telethon listener no arranca: faltan TELETHON_API_ID, TELETHON_API_HASH, WATCH_CHANNEL u OWNER_ID")
        return

    from telethon import TelegramClient, events
    from telethon.sessions import StringSession

    session = StringSession(TELETHON_SESSION) if TELETHON_SESSION else StringSession()
    client = TelegramClient(session, int(TELETHON_API_ID), TELETHON_API_HASH)

    await client.start()
    logger.info("Telethon client started")

    # Inicializar cola FIFO y arrancar consumer
    global _telethon_send_q
    import asyncio as _aio
    _telethon_send_q = _aio.Queue()

    async def _telethon_consumer():
        while True:
            coro = await _telethon_send_q.get()
            try:
                await coro
            except Exception as e:
                logger.error(f"[telethon consumer] {e}")

    _aio.create_task(_telethon_consumer())

    # Resolver el canal
    try:
        watch_entity = await client.get_entity(WATCH_CHANNEL)
        watch_id = watch_entity.id
        logger.info(f"Escuchando canal: {WATCH_CHANNEL} (id={watch_id})")
    except Exception as e:
        logger.error(f"No se pudo resolver el canal {WATCH_CHANNEL}: {e}")
        await client.disconnect()
        return

    # Buffer para álbumes (media_group)
    _album_buffer: dict = {}

    @client.on(events.NewMessage(chats=watch_entity))
    async def on_channel_message(event):
        msg = event.message

        # Solo procesar mensajes con foto(s)
        if not msg.photo and not msg.grouped_id:
            return

        grouped_id = msg.grouped_id

        if grouped_id:
            # Primer mensaje del álbum: crear evento y encolar YA (en orden de llegada)
            if grouped_id not in _album_buffer:
                ready_event = asyncio.Event()
                _album_buffer[grouped_id] = {"msgs": [], "text": "", "ready": ready_event}
                # Tras 2.5s señalar que el buffer está completo
                asyncio.get_event_loop().call_later(2.5, ready_event.set)
                # Poner en cola AHORA para respetar orden de llegada
                _telethon_send_q.put_nowait(
                    _forward_album_to_owner(client, ptb_app, _album_buffer, grouped_id, ready_event)
                )
            _album_buffer[grouped_id]["msgs"].append(msg)
            if msg.text:
                _album_buffer[grouped_id]["text"] = msg.text
        else:
            # Foto individual: encolar directamente en orden de llegada
            if msg.photo:
                _telethon_send_q.put_nowait(
                    _forward_single_to_owner(client, ptb_app, msg)
                )

    await client.run_until_disconnected()


async def _download_photo_bytes(client, msg) -> bytes | None:
    """Descarga la foto de un mensaje Telethon como bytes."""
    try:
        return await client.download_media(msg, bytes)
    except Exception as e:
        logger.warning(f"Error descargando foto Telethon: {e}")
        return None



async def _forward_single_to_owner(client, ptb_app, msg):
    """Reenvía un mensaje con foto individual al owner con botones ✅/❌."""
    import time
    photo_bytes = await _download_photo_bytes(client, msg)
    if not photo_bytes:
        return

    key = f"ch_{int(time.time())}_{msg.id}"
    original_text = msg.text or msg.message or ""

    _pending_channel_msgs[key] = {
        "photo_bytes_list": [photo_bytes],
        "original_text": original_text,
    }

    caption = f"📡 *Nuevo producto del canal*\n\n{original_text}" if original_text else "📡 *Nuevo producto del canal*"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Publicar", callback_data=f"ch_ok_{key}"),
        InlineKeyboardButton("❌ Descartar", callback_data=f"ch_no_{key}"),
    ]])

    await ptb_app.bot.send_photo(
        chat_id=OWNER_ID,
        photo=photo_bytes,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def _forward_album_to_owner(client, ptb_app, album_buffer: dict, grouped_id: int, ready_event):
    """Reenvía un álbum de fotos al owner con botones ✅/❌. Espera a que el buffer esté completo."""
    import time
    # Esperar a que lleguen todos los mensajes del álbum (2.5s)
    await ready_event.wait()

    group = album_buffer.pop(grouped_id, None)
    if not group:
        return

    msgs = group["msgs"]
    original_text = group["text"]

    # Descargar todas las fotos
    photos_bytes = []
    for m in msgs:
        b = await _download_photo_bytes(client, m)
        if b:
            photos_bytes.append(b)

    if not photos_bytes:
        return

    key = f"ch_{int(time.time())}_{grouped_id}"
    _pending_channel_msgs[key] = {
        "photo_bytes_list": photos_bytes,
        "original_text": original_text,
    }

    caption_text = f"📡 *Nuevo producto del canal* ({len(photos_bytes)} fotos)\n\n{original_text}" if original_text else f"📡 *Nuevo producto del canal* ({len(photos_bytes)} fotos)"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Publicar", callback_data=f"ch_ok_{key}"),
        InlineKeyboardButton("❌ Descartar", callback_data=f"ch_no_{key}"),
    ]])

    if len(photos_bytes) == 1:
        await ptb_app.bot.send_photo(
            chat_id=OWNER_ID,
            photo=photos_bytes[0],
            caption=caption_text,
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        from telegram import InputMediaPhoto as IMP
        media = [IMP(media=b) for b in photos_bytes]
        media[0] = IMP(media=photos_bytes[0], caption=caption_text, parse_mode="Markdown")
        await ptb_app.bot.send_media_group(chat_id=OWNER_ID, media=media)
        await ptb_app.bot.send_message(
            chat_id=OWNER_ID,
            text="¿Qué hacemos con este producto?",
            reply_markup=kb,
        )


# ---------------------------------------------------------------------------
# Callbacks para ✅/❌ del canal externo
# ---------------------------------------------------------------------------

_fwd_album_buffer: dict = {}  # media_group_id → {file_ids, text, user_id, chat_id}
_nl_album_buffer: dict = {}   # media_group_id → {file_ids, caption, user_id, chat_id} para newsletter (otro canal)
_nl_own_album_buffer: dict = {}  # media_group_id → {file_ids, caption, user_id, chat_id} para newsletter (mi canal)


async def _start_fwd_queue_job(context: ContextTypes.DEFAULT_TYPE):
    """Job que arranca la cola tras 3.5s, mostrando el total y el primer producto."""
    data = context.job.data
    user_id = data["user_id"]
    chat_id = data["chat_id"]
    total = len(_fwd_queue.get(user_id, []))
    if total:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📋 {total} producto{'s' if total != 1 else ''} en cola. Empezando con el primero:",
        )
    await _show_next_from_queue(user_id, chat_id, context.bot)


async def _show_next_from_queue(user_id: int, chat_id: int, bot):
    """Muestra el siguiente mensaje de la cola del usuario, si hay."""
    import time
    queue = _fwd_queue.get(user_id, [])
    if not queue:
        _fwd_active.discard(user_id)
        await bot.send_message(chat_id=chat_id, text="✅ Cola vacía, todos los productos procesados.")
        return

    item = queue.pop(0)
    photo_bytes_list = item["photo_bytes_list"]
    original_text = item["original_text"]
    remaining = len(queue)

    key = f"ch_{int(time.time())}_{user_id}"
    _pending_channel_msgs[key] = {"photo_bytes_list": photo_bytes_list, "original_text": original_text}

    caption = f"📡 *Producto reenviado*"
    if remaining:
        caption += f" — quedan {remaining} en cola"
    if original_text:
        caption += f"\n\n{original_text}"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Publicar", callback_data=f"ch_ok_{key}"),
        InlineKeyboardButton("❌ Descartar", callback_data=f"ch_no_{key}"),
    ]])

    if len(photo_bytes_list) == 1:
        await bot.send_photo(chat_id=chat_id, photo=photo_bytes_list[0], caption=caption, parse_mode="Markdown", reply_markup=kb)
    else:
        media = [InputMediaPhoto(media=b) for b in photo_bytes_list]
        media[0] = InputMediaPhoto(media=photo_bytes_list[0], caption=caption, parse_mode="Markdown")
        await bot.send_media_group(chat_id=chat_id, media=media)
        await bot.send_message(chat_id=chat_id, text="¿Qué hacemos con este producto?", reply_markup=kb)


async def _process_forwarded_album(context: ContextTypes.DEFAULT_TYPE):
    """Job que se dispara 2s después de recibir el primer mensaje del álbum reenviado."""
    import time
    mg_id = context.job.data
    group = _fwd_album_buffer.pop(mg_id, None)
    if not group:
        return

    user_id = group["user_id"]
    chat_id = group["chat_id"]
    original_text = group["text"]

    photo_bytes_list = []
    for fid in group["file_ids"]:
        try:
            f = await context.bot.get_file(fid)
            photo_bytes_list.append(bytes(await f.download_as_bytearray()))
        except Exception as e:
            logger.error(f"Error descargando foto álbum reenviado: {e}")

    if not photo_bytes_list:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ No pude descargar las fotos.")
        return

    # Encolar; si es el primero, programar job que arranca la cola en 3.5s
    _fwd_queue.setdefault(user_id, []).append({"photo_bytes_list": photo_bytes_list, "original_text": original_text})
    if user_id not in _fwd_active:
        _fwd_active.add(user_id)
        context.application.job_queue.run_once(
            _start_fwd_queue_job, 3.5,
            data={"user_id": user_id, "chat_id": chat_id},
            name=f"startqueue_{user_id}",
        )


async def handle_forwarded_channel_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """El usuario reenvía manualmente un mensaje del canal al bot."""
    msg = update.message
    user_id = update.effective_user.id

    # Si está en modo newsletter, manejar según fuente (auto-detectada)
    nl_state = user_states.get(user_id, {}).get("state", "")
    if nl_state.startswith("newsletter_") and nl_state != "newsletter_confirm" and not nl_state.endswith("_waiting_hacoo"):
        section = user_states[user_id].get("newsletter_section", "zapatillas")
        file_id = msg.photo[-1].file_id if msg.photo else None
        caption = msg.caption or msg.text or ""
        media_group_id = msg.media_group_id

        # Auto-detectar fuente: ¿es de mi canal o de otro?
        forward_origin = msg.forward_origin
        is_own_channel = False
        if forward_origin:
            # Caso 1: reenviado desde un canal → comparar chat.id con CHANNEL_ID
            if hasattr(forward_origin, "chat"):
                origin_chat_id = str(forward_origin.chat.id).lstrip("-")
                own_channel_id = str(CHANNEL_ID).lstrip("-") if CHANNEL_ID else ""
                is_own_channel = bool(own_channel_id and origin_chat_id == own_channel_id)
            # Caso 2: reenviado desde el propio bot (Trent Bot) → es mi canal
            elif hasattr(forward_origin, "sender_user") and forward_origin.sender_user:
                sender = forward_origin.sender_user
                bot_id = context.bot.id if context and hasattr(context, "bot") else None
                is_own_channel = bool(sender.is_bot and bot_id and sender.id == bot_id)

        if is_own_channel:
            nl_source = "own"
        elif forward_origin:
            nl_source = "other"
        else:
            nl_source = user_states[user_id].get("nl_source", "own")

        user_states[user_id]["nl_source"] = nl_source

        if nl_source == "other":
            # Otro canal: bufferear álbum completo antes de procesar
            if media_group_id:
                if media_group_id not in _nl_album_buffer:
                    _nl_album_buffer[media_group_id] = {"file_ids": [], "caption": caption, "user_id": user_id, "chat_id": msg.chat.id}
                    context.job_queue.run_once(
                        _nl_album_flush_job,
                        when=2.0,
                        data={"media_group_id": media_group_id, "section": section},
                        name=f"nlalbum_{media_group_id}",
                    )
                if file_id:
                    _nl_album_buffer[media_group_id]["file_ids"].append(file_id)
                if caption:
                    _nl_album_buffer[media_group_id]["caption"] = caption
            else:
                await _handle_newsletter_forwarded(update, context, user_id, section, [file_id] if file_id else [], caption)
            return
        else:
            # Mi canal: bufferear álbum para recoger todas las imágenes
            if media_group_id:
                if media_group_id not in _nl_own_album_buffer:
                    _nl_own_album_buffer[media_group_id] = {"file_ids": [], "caption": caption, "user_id": user_id, "chat_id": msg.chat.id}
                    context.job_queue.run_once(
                        _nl_own_album_flush_job,
                        when=2.0,
                        data={"media_group_id": media_group_id, "section": section},
                        name=f"nlownalbum_{media_group_id}",
                    )
                if file_id:
                    _nl_own_album_buffer[media_group_id]["file_ids"].append(file_id)
                if caption:
                    _nl_own_album_buffer[media_group_id]["caption"] = caption
            else:
                # Foto suelta sin álbum
                await _handle_newsletter_photo(update, context, user_id, section)
            return

    # Si está en modo newsletter waiting_hacoo, redirigir al handler existente
    if nl_state.startswith("newsletter_") and nl_state != "newsletter_confirm":
        section = user_states[user_id].get("newsletter_section", "zapatillas")
        await _handle_newsletter_photo(update, context, user_id, section)
        return

    if OWNER_ID and user_id != OWNER_ID:
        return

    if not msg.photo:
        await msg.reply_text("⚠️ Reenvía un mensaje con foto del canal.")
        return

    original_text = msg.caption or ""
    file_id = msg.photo[-1].file_id
    mg_id = msg.media_group_id

    if mg_id:
        # Álbum: bufferizar y esperar 2s a que lleguen todas las fotos
        if mg_id not in _fwd_album_buffer:
            _fwd_album_buffer[mg_id] = {
                "file_ids": [],
                "text": original_text,
                "user_id": user_id,
                "chat_id": update.effective_chat.id,
            }
            context.application.job_queue.run_once(_process_forwarded_album, 2, data=mg_id, name=f"fwdalbum_{mg_id}")
        _fwd_album_buffer[mg_id]["file_ids"].append(file_id)
        if original_text:
            _fwd_album_buffer[mg_id]["text"] = original_text
    else:
        # Foto individual: encolar
        try:
            f = await context.bot.get_file(file_id)
            photo_bytes = bytes(await f.download_as_bytearray())
        except Exception as e:
            logger.error(f"Error descargando foto reenviada: {e}")
            await msg.reply_text("⚠️ No pude descargar la foto.")
            return

        _fwd_queue.setdefault(user_id, []).append({"photo_bytes_list": [photo_bytes], "original_text": original_text})
        if user_id not in _fwd_active:
            _fwd_active.add(user_id)
            context.application.job_queue.run_once(
                _start_fwd_queue_job, 3.5,
                data={"user_id": user_id, "chat_id": update.effective_chat.id},
                name=f"startqueue_{user_id}",
            )



async def callback_channel_ok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """El usuario aprueba el producto del canal → pide captura de Hacoo."""
    query = update.callback_query
    await query.answer()
    key = query.data.replace("ch_ok_", "")
    pending = _pending_channel_msgs.get(key)
    if not pending:
        await query.edit_message_text("❌ Este producto ya no está disponible.")
        return

    user_id = query.from_user.id
    original_text = pending.get("original_text", "")
    urls = re.findall(r'https?://\S+', original_text)

    user_states[user_id] = {
        "state": "waiting_hacoo_for_channel",
        "channel_key": key,
        "photos": [],
        "price": "",
        "colores": "",
        "link": "",
        "title": "",
        "marca": "",
        "categoria": "",
        "image_url": "",
        "pending_urls": urls,       # lista de URLs a procesar
        "url_index": 0,             # cuál estamos procesando ahora
        "url_affiliate_map": {},    # {url_original: affiliate_link}
    }

    is_yepex = bool(re.search(r'yepex|yepexpress', original_text, re.IGNORECASE))
    user_states[user_id]["is_yepex"] = is_yepex

    n = len(urls)
    if is_yepex:
        user_states[user_id]["state"] = "waiting_yepex_url_for_channel"
        texto_ok = "🟠 Producto Yepex detectado. Envíame el *link del producto* y lo pondré en el mensaje."
    elif n > 1:
        texto_ok = f"✅ Este mensaje tiene {n} links. Envíame la captura de Hacoo del *primero* (1/{n})."
    else:
        texto_ok = "✅ Perfecto. Ahora envíame la captura del producto en Hacoo para generar el link de afiliado."
    try:
        await query.edit_message_text(texto_ok, parse_mode="Markdown")
    except Exception:
        try:
            await query.edit_message_caption(texto_ok, parse_mode="Markdown")
        except Exception:
            await query.message.reply_text(texto_ok, parse_mode="Markdown")


async def callback_channel_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """El usuario descarta el producto del canal."""
    query = update.callback_query
    await query.answer()
    key = query.data.replace("ch_no_", "")
    _pending_channel_msgs.pop(key, None)
    user_id = query.from_user.id
    try:
        await query.edit_message_text("❌ Producto descartado.")
    except Exception:
        try:
            await query.edit_message_caption("❌ Producto descartado.")
        except Exception:
            await query.message.reply_text("❌ Producto descartado.")
    await _show_next_from_queue(user_id, query.message.chat.id, context.bot)





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


# ---------------------------------------------------------------------------
# NEWSLETTER — almacenamiento y lógica
# ---------------------------------------------------------------------------

_NEWSLETTER_FILE = "/tmp/newsletter_products.json"
_NEWSLETTER_SECTIONS = {"zapatillas": "👟 Zapatillas", "hombre": "👔 Ropa Hombre", "mujer": "👗 Ropa Mujer"}


def _load_newsletter() -> dict:
    try:
        with open(_NEWSLETTER_FILE) as f:
            return json.load(f)
    except Exception:
        return {"zapatillas": [], "hombre": [], "mujer": []}


def _save_newsletter(data: dict):
    try:
        with open(_NEWSLETTER_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error guardando newsletter: {e}")


def _build_newsletter_html(data: dict, week: int) -> str:
    def products_html(items: list, icon: str) -> str:
        if not items:
            return f'<div style="padding:20px 16px;text-align:center;"><p style="color:#aaa;font-size:13px;">Sin productos esta semana.</p></div>'
        rank_emojis = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        html = ""
        for i, p in enumerate(items):
            rank = rank_emojis[i] if i < len(rank_emojis) else f"{i+1}."
            badge = '<div class="badge badge-gold">TOP #1</div>' if i == 0 else ""
            imgs = p.get("image_urls") or ([p["image_url"]] if p.get("image_url") else [])
            if len(imgs) > 1:
                # Múltiples fotos: fila horizontal con scroll
                imgs_html = "".join(
                    f'<img src="{u}" width="76" height="76" style="display:inline-block;width:76px;height:76px;object-fit:cover;margin-right:4px;border-radius:2px;" alt="">'
                    for u in imgs
                )
                img_block = f'<div style="overflow-x:auto;white-space:nowrap;margin-bottom:10px;">{imgs_html}</div>'
                html += f'''
    <div class="product">
      <div class="product-top">
        <div class="product-rank-cell">{rank}</div>
        <div class="product-info-cell" style="padding-left:0;">
          {badge}
          <div class="product-name">{p["name"]}</div>
        </div>
      </div>
      {img_block}
      <a href="{p["link"]}" class="product-btn">Ver producto &#8594;</a>
    </div>'''
            else:
                img_content = f'<img src="{imgs[0]}" width="76" height="76" style="display:block;width:76px;height:76px;object-fit:cover;" alt="">' if imgs else icon
                html += f'''
    <div class="product">
      <div class="product-top">
        <div class="product-rank-cell">{rank}</div>
        <div class="product-img-cell"><div class="product-img">{img_content}</div></div>
        <div class="product-info-cell">
          {badge}
          <div class="product-name">{p["name"]}</div>
        </div>
      </div>
      <a href="{p["link"]}" class="product-btn">Ver producto &#8594;</a>
    </div>'''
        return html

    zap = products_html(data.get("zapatillas", []), "👟")
    hom = products_html(data.get("hombre", []), "🧥")
    muj = products_html(data.get("mujer", []), "👗")
    nz = len(data.get("zapatillas", []))
    nh = len(data.get("hombre", []))
    nm = len(data.get("mujer", []))
    muj_count = f"{nm} picks" if nm else "próximamente"

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>TRENT Newsletter Semanal</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #f4f4f4; font-family: Arial, Helvetica, sans-serif; -webkit-text-size-adjust: 100%; }}
    .wrapper {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
    .header {{ background: #111111; padding: 28px 20px; text-align: center; }}
    .header-logo {{ font-size: 40px; font-weight: 900; color: #ffffff; letter-spacing: 4px; }}
    .header-logo span {{ color: #e8002d; }}
    .header-sub {{ font-size: 11px; color: #777; letter-spacing: 2px; text-transform: uppercase; margin-top: 6px; }}
    .hero {{ background: #e8002d; padding: 24px 20px; text-align: center; }}
    .hero-title {{ font-size: 26px; font-weight: 900; color: #ffffff; text-transform: uppercase; line-height: 1.2; }}
    .hero-sub {{ font-size: 13px; color: rgba(255,255,255,0.9); margin-top: 8px; }}
    .intro {{ background: #ffffff; padding: 20px; border-bottom: 3px solid #f4f4f4; }}
    .intro p {{ font-size: 14px; color: #444; line-height: 1.7; }}
    .intro strong {{ color: #111; }}
    .section-wrap {{ background: #ffffff; padding: 0 0 8px 0; }}
    .section-bar {{ background: #111111; margin: 16px 16px 0 16px; padding: 14px 16px; display: table; width: calc(100% - 32px); }}
    .section-icon {{ display: table-cell; font-size: 22px; vertical-align: middle; width: 36px; }}
    .section-name {{ display: table-cell; font-size: 14px; font-weight: 900; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; vertical-align: middle; }}
    .section-count {{ display: table-cell; font-size: 11px; color: #888; text-align: right; vertical-align: middle; white-space: nowrap; }}
    .product {{ background: #ffffff; margin: 8px 16px; padding: 14px; border: 1px solid #eeeeee; border-left: 4px solid #e8002d; }}
    .product-top {{ display: table; width: 100%; margin-bottom: 10px; }}
    .product-rank-cell {{ display: table-cell; width: 30px; vertical-align: top; font-size: 18px; }}
    .product-img-cell {{ display: table-cell; width: 80px; vertical-align: top; padding-right: 12px; }}
    .product-img {{ width: 76px; height: 76px; background: #f8f8f8; border: 1px solid #eee; display: block; text-align: center; line-height: 76px; font-size: 32px; overflow: hidden; }}
    .product-info-cell {{ display: table-cell; vertical-align: top; }}
    .badge {{ display: inline-block; padding: 3px 8px; font-size: 10px; font-weight: 900; border-radius: 2px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }}
    .badge-gold {{ background: #FFD700; color: #111; }}
    .product-name {{ font-size: 14px; font-weight: 700; color: #111; line-height: 1.4; margin-bottom: 10px; }}
    .product-btn {{ display: block; background: #e8002d; color: #ffffff; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 10px 16px; text-decoration: none; text-align: center; }}
    .divider {{ height: 12px; background: #f4f4f4; }}
    .code-section {{ background: #111111; padding: 28px 20px; text-align: center; }}
    .code-label {{ font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }}
    .code-box {{ font-size: 44px; font-weight: 900; color: #e8002d; letter-spacing: 4px; margin-bottom: 6px; }}
    .code-desc {{ font-size: 13px; color: #999; }}
    .cta {{ background: #f4f4f4; padding: 28px 20px; text-align: center; }}
    .cta-text {{ font-size: 15px; color: #444; line-height: 1.6; margin-bottom: 18px; }}
    .cta-text strong {{ color: #111; }}
    .cta-btn {{ display: block; background: #111111; color: #ffffff; font-size: 15px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; padding: 16px 24px; text-decoration: none; }}
    .footer {{ background: #ffffff; padding: 20px; text-align: center; border-top: 1px solid #eee; }}
    .footer p {{ font-size: 11px; color: #aaa; line-height: 2; }}
    .footer a {{ color: #aaa; }}
  </style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="header-logo">TREN<span>T</span></div>
    <div class="header-sub">Links · Moda · Marca</div>
  </div>
  <div class="hero">
    <div class="hero-title">&#128293; Los mejores productos de la semana</div>
    <div class="hero-sub">Zapatillas · Ropa Hombre · Ropa Mujer</div>
  </div>
  <div class="intro">
    <p>Hola! Esta semana he seleccionado <strong>los mejores productos de Hacoo</strong> divididos por categoría. Todos los links están verificados. Recuerda usar el código <strong>TRENT14</strong> para un <strong>&#8722;14% en tu primera compra</strong> &#128293;</p>
  </div>
  <div class="section-wrap">
    <div class="section-bar">
      <div class="section-icon">&#128095;</div>
      <div class="section-name">Zapatillas de la semana</div>
      <div class="section-count">{nz} picks</div>
    </div>
    {zap}
  </div>
  <div class="divider"></div>
  <div class="section-wrap">
    <div class="section-bar">
      <div class="section-icon">&#128084;</div>
      <div class="section-name">Ropa Hombre de la semana</div>
      <div class="section-count">{nh} picks</div>
    </div>
    {hom}
  </div>
  <div class="divider"></div>
  <div class="section-wrap">
    <div class="section-bar">
      <div class="section-icon">&#128161;</div>
      <div class="section-name">Ropa Mujer de la semana</div>
      <div class="section-count">{muj_count}</div>
    </div>
    {muj}
  </div>
  <div class="divider"></div>
  <div class="code-section">
    <div class="code-label">Código descuento · Solo 1ª compra</div>
    <div class="code-box">TRENT14</div>
    <div class="code-desc">&#8722;14% en tu primera compra en Hacoo</div>
  </div>
  <div class="cta">
    <p class="cta-text">¿Quieres recibir links <strong>cada día</strong>?<br>Únete al canal con <strong>41.000 miembros</strong>.</p>
    <a href="https://t.me/trentthacoo" class="cta-btn">&#128241; Unirme al canal de Telegram</a>
  </div>
  <div class="footer">
    <p>
      @trent_wave · @trentthacoo<br>
      <a href="https://trentlinks.netlify.app">trentlinks.netlify.app</a><br><br>
      <a href="#">Cancelar suscripción</a>
    </p>
  </div>
</div>
</body>
</html>"""


def _brevo_get_contacts() -> list:
    """Obtiene todos los contactos de Brevo."""
    if not BREVO_API_KEY:
        return []
    emails = []
    offset = 0
    limit = 500
    while True:
        try:
            r = requests.get(
                "https://api.brevo.com/v3/contacts",
                headers={"api-key": BREVO_API_KEY, "Accept": "application/json"},
                params={"limit": limit, "offset": offset},
                timeout=15,
            )
            data = r.json()
            contacts = data.get("contacts", [])
            for c in contacts:
                email = c.get("email")
                # Saltar contactos desuscritos o bloqueados
                if not email or c.get("emailBlacklisted") or c.get("smsBlacklisted"):
                    continue
                emails.append({"email": email, "name": c.get("attributes", {}).get("FIRSTNAME", "") or c.get("attributes", {}).get("LASTNAME", "")})
            if len(contacts) < limit:
                break
            offset += limit
        except Exception as e:
            logger.error(f"Brevo get contacts error: {e}")
            break
    return emails


def _brevo_send_newsletter(subject: str, html_content: str, contacts: list) -> tuple[bool, str]:
    """Envía el newsletter via Brevo transactional API."""
    if not BREVO_API_KEY:
        return False, "BREVO_API_KEY no configurada"
    if not contacts:
        return False, "Sin suscriptores"

    # Brevo permite hasta 50 destinatarios por email transaccional, enviamos en lotes
    errors = []
    sent = 0
    batch_size = 50
    for i in range(0, len(contacts), batch_size):
        batch = contacts[i:i+batch_size]
        to = [{"email": c["email"], "name": c.get("name") or c["email"].split("@")[0]} for c in batch]
        payload = {
            "sender": {"name": "TRENT", "email": "trenttwave@gmail.com"},
            "to": to,
            "subject": subject,
            "htmlContent": html_content,
        }
        try:
            r = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            if r.status_code in (200, 201, 202):
                sent += len(batch)
            else:
                errors.append(f"Lote {i//batch_size+1}: {r.status_code} {r.text[:100]}")
        except Exception as e:
            errors.append(f"Lote {i//batch_size+1}: {e}")

    if sent > 0:
        return True, f"Enviado a {sent} suscriptores" + (f" (errores: {'; '.join(errors)})" if errors else "")
    return False, "; ".join(errors) or "Error desconocido"


async def cmd_newsletter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entra en modo newsletter y pregunta qué sección añadir."""
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        return
    data = _load_newsletter()
    totals = {k: len(v) for k, v in data.items()}
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"👟 Zapatillas ({totals['zapatillas']})", callback_data="nl_sec_zapatillas"),
        InlineKeyboardButton(f"👔 Hombre ({totals['hombre']})", callback_data="nl_sec_hombre"),
    ],[
        InlineKeyboardButton(f"👗 Mujer ({totals['mujer']})", callback_data="nl_sec_mujer"),
    ]])
    await update.message.reply_text(
        "📰 *Modo Newsletter*\n\n¿A qué sección quieres añadir productos?",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def callback_newsletter_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """El usuario elige la sección de la newsletter."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    section = query.data.replace("nl_sec_", "")
    section_name = _NEWSLETTER_SECTIONS.get(section, section)

    # Sin preguntar la fuente: el bot la detecta automáticamente según el mensaje recibido
    user_states[user_id] = {"state": f"newsletter_{section}", "newsletter_section": section}
    await query.edit_message_text(
        f"📰 {section_name}\n\n"
        f"Envíame el producto:\n"
        f"• Reenvía un mensaje de tu canal (link ya incluido)\n"
        f"• Reenvía un mensaje de otro canal (te genero el link)\n"
        f"• Envía una captura de Hacoo directamente"
    )


async def callback_newsletter_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """El usuario elige si el producto viene de su canal o de otro."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    # data: nl_src_own_zapatillas  o  nl_src_other_zapatillas
    parts = query.data.split("_", 3)  # ['nl', 'src', 'own'/'other', section]
    source = parts[2]  # 'own' o 'other'
    section = parts[3]
    section_name = _NEWSLETTER_SECTIONS.get(section, section)

    user_states[user_id] = {"state": f"newsletter_{section}", "newsletter_section": section, "nl_source": source}

    if source == "own":
        await query.edit_message_text(
            f"📰 {section_name} — Mi canal\n\n"
            f"Reenvíame el mensaje de tu canal. El link de afiliado ya viene incluido y lo guardaré directamente."
        )
    else:
        await query.edit_message_text(
            f"📰 {section_name} — Otro canal\n\n"
            f"Reenvíame la captura del producto en Hacoo y generaré tu link de afiliado automáticamente."
        )


async def cmd_ver_newsletter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los productos guardados para la newsletter."""
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        return
    data = _load_newsletter()
    lines = ["📰 *Newsletter actual:*\n"]
    for key, label in _NEWSLETTER_SECTIONS.items():
        items = data.get(key, [])
        lines.append(f"*{label}* ({len(items)} productos)")
        if items:
            for i, p in enumerate(items):
                lines.append(f"  {i+1}. {p['name']} — {p['link']}")
        else:
            lines.append("  _(vacío)_")
        lines.append("")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_enviar_newsletter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera el email HTML y pide confirmación antes de enviarlo."""
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        return

    data = _load_newsletter()
    total = sum(len(v) for v in data.values())
    if total == 0:
        await update.message.reply_text("❌ No hay productos guardados en la newsletter.")
        return

    week = datetime.datetime.now().isocalendar()[1]
    html = _build_newsletter_html(data, week)

    # Guardar HTML en fichero temporal
    html_path = "/tmp/newsletter_preview.html"
    with open(html_path, "w") as f:
        f.write(html)

    contacts = _brevo_get_contacts()
    user_states[user_id] = {"state": "newsletter_confirm", "html": html, "contacts_count": len(contacts)}

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Enviar newsletter", callback_data="nl_send_confirm"),
        InlineKeyboardButton("❌ Cancelar", callback_data="nl_send_cancel"),
    ]])
    await update.message.reply_document(
        document=open(html_path, "rb"),
        filename=f"newsletter_semana{week}.html",
        caption=(
            f"📰 *Preview newsletter Semana {week}*\n\n"
            f"👟 Zapatillas: {len(data['zapatillas'])} productos\n"
            f"👔 Hombre: {len(data['hombre'])} productos\n"
            f"👗 Mujer: {len(data['mujer'])} productos\n\n"
            f"📧 Suscriptores: {len(contacts)}\n\n"
            f"Abre el HTML para previsualizar. ¿Lo enviamos?"
        ),
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def callback_newsletter_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma o cancela el envío de la newsletter."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_states.get(user_id, {})

    if query.data == "nl_send_cancel":
        user_states.pop(user_id, None)
        await query.edit_message_caption("❌ Envío cancelado.")
        return

    html = state.get("html", "")
    if not html:
        await query.edit_message_caption("❌ No hay HTML guardado. Usa /enviar de nuevo.")
        return

    await query.edit_message_caption("⏳ Enviando newsletter...")
    contacts = _brevo_get_contacts()
    week = datetime.datetime.now().isocalendar()[1]
    subject = f"🔥 TRENT — Los mejores productos de la semana {week}"
    ok, msg = _brevo_send_newsletter(subject, html, contacts)

    if ok:
        _save_newsletter({"zapatillas": [], "hombre": [], "mujer": []})
        user_states.pop(user_id, None)
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"✅ Newsletter enviada. {msg}\n\nProductos limpiados para la semana siguiente.",
        )
    else:
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"❌ Error al enviar: {msg}",
        )


async def _nl_save_all(chat_id: int, user_id: int, section: str, affiliate_map: dict, bot):
    """Guarda todos los productos del affiliate_map en la newsletter."""
    section_name = _NEWSLETTER_SECTIONS.get(section, section)
    nl_photo_groups = user_states.get(user_id, {}).get("nl_photo_groups", [])
    data = _load_newsletter()
    added = []
    for i, (orig_url, info) in enumerate(affiliate_map.items()):
        n_name = info.get("name") or "Producto"
        # Obtener URLs públicas de las fotos de este producto
        image_urls = []
        # Primero usar imagen de Hacoo si existe (ya es URL pública)
        hacoo_url = info.get("image_url") or ""
        if hacoo_url and hacoo_url.startswith("http"):
            image_urls.append(hacoo_url)
        # Añadir fotos del álbum original para este producto
        group = nl_photo_groups[i] if i < len(nl_photo_groups) else []
        for fid in group:
            if fid and not fid.startswith("http"):
                try:
                    tg_file = await bot.get_file(fid)
                    image_urls.append(tg_file.file_path)
                except Exception:
                    pass
            elif fid.startswith("http"):
                image_urls.append(fid)
        # Si no hay ninguna imagen de Hacoo, usar solo las del álbum
        if not image_urls and hacoo_url and not hacoo_url.startswith("http"):
            try:
                tg_file = await bot.get_file(hacoo_url)
                image_urls.append(tg_file.file_path)
            except Exception:
                pass
        data[section].append({"name": n_name, "link": info["link"], "image_urls": image_urls, "image_url": image_urls[0] if image_urls else "", "price": info.get("price", "")})
        added.append(f"• {n_name} → {info['link']}")
    _save_newsletter(data)
    user_states[user_id]["state"] = f"newsletter_{section}"
    resumen = "\n".join(added)
    await bot.send_message(
        chat_id=chat_id,
        text=f"✅ {len(added)} producto{'s' if len(added)!=1 else ''} añadido{'s' if len(added)!=1 else ''} a {section_name}:\n\n{resumen}\n\nReenvía otro mensaje o /newsletter para cambiar de sección."
    )


def _clean_product_name(name: str) -> str:
    """Limpia el nombre del producto: quita (yepex), emojis y espacios extra."""
    name = re.sub(r'\(yepex\)', "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r'[\U00010000-\U0010ffff]|[☀-➿]|[\uD800-\uDFFF]', "", name).strip()
    return name.strip(" →—>-🔗").strip()


def _extract_name_for_url(text: str, url: str) -> str:
    """Extrae el nombre del producto buscando la línea antes del link en el texto."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if url in line:
            # Buscar nombre en la misma línea o en la anterior
            name_line = ""
            if i > 0:
                prev = re.sub(r'https?://\S+', "", lines[i-1]).strip()
                if prev:
                    name_line = prev
            if not name_line:
                name_line = re.sub(r'https?://\S+', "", line).strip()
            # Limpiar emojis de ranking y símbolos
            name_line = re.sub(r'^[\s🥇🥈🥉1-9️⃣🔟⭐🏆\d\.\:\-→]+', "", name_line).strip()
            name_line = name_line.strip(" →—>-🔗MH:").strip()
            return name_line
    return ""


async def _nl_save_direct_hacoo(chat_id: int, user_id: int, section: str, bot):
    """Guarda en la newsletter un producto de captura directa Hacoo (con nombre y fotos del usuario)."""
    section_name = _NEWSLETTER_SECTIONS.get(section, section)
    link = user_states[user_id].get("nl_direct_link", "")
    image_url = user_states[user_id].get("nl_direct_image_url", "")
    price = user_states[user_id].get("nl_direct_price", "")
    nombre = user_states[user_id].get("nl_direct_name", "") or "Producto"
    photo_ids = user_states[user_id].get("nl_direct_photos", [])

    image_urls = []
    if image_url and image_url.startswith("http"):
        image_urls.append(image_url)
    for fid in photo_ids:
        try:
            tg_file = await bot.get_file(fid)
            image_urls.append(tg_file.file_path)
        except Exception:
            pass

    data = _load_newsletter()
    data[section].append({"name": nombre, "link": link, "image_urls": image_urls, "image_url": image_urls[0] if image_urls else "", "price": price})
    _save_newsletter(data)
    n = len(data[section])
    user_states[user_id]["state"] = f"newsletter_{section}"
    img_info = f" ({len(image_urls)} imágenes)" if len(image_urls) > 1 else ""
    await bot.send_message(chat_id=chat_id, text=f"✅ Añadido a {section_name} (#{n}){img_info}\n\n{nombre}\n{link}\n\nReenvía otro mensaje o /newsletter para cambiar de sección.")


async def cmd_listo_nl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el producto de captura directa Hacoo cuando el usuario ya envió nombre y fotos."""
    user_id = update.effective_user.id
    nl_state = user_states.get(user_id, {}).get("state", "")
    if not nl_state.endswith("_waiting_name_photo"):
        return
    section = user_states[user_id].get("newsletter_section", "zapatillas")
    nombre = user_states[user_id].get("nl_direct_name", "")
    photos = user_states[user_id].get("nl_direct_photos", [])
    if not nombre:
        await update.message.reply_text("Aún no me has dicho el nombre del producto.")
        return
    if not photos:
        await update.message.reply_text("Aún no me has enviado ninguna foto.")
        return
    await _nl_save_direct_hacoo(update.message.chat.id, user_id, section, context.bot)


async def _nl_album_flush_job(context):
    """Procesa el álbum de newsletter cuando han llegado todas las fotos (otro canal)."""
    data = context.job.data
    media_group_id = data["media_group_id"]
    section = data["section"]
    buf = _nl_album_buffer.pop(media_group_id, None)
    if not buf:
        return
    user_id = buf["user_id"]
    file_ids = buf["file_ids"]
    caption = buf["caption"]
    await _handle_newsletter_forwarded(context, context, user_id, section, file_ids, caption, bot=context.bot, chat_id=buf["chat_id"])


async def _nl_own_album_flush_job(context):
    """Procesa el álbum de newsletter cuando han llegado todas las fotos (mi canal)."""
    data = context.job.data
    media_group_id = data["media_group_id"]
    section = data["section"]
    buf = _nl_own_album_buffer.pop(media_group_id, None)
    if not buf:
        return
    user_id = buf["user_id"]
    chat_id = buf["chat_id"]
    file_ids = buf["file_ids"]
    caption = buf["caption"]
    section_name = _NEWSLETTER_SECTIONS.get(section, section)

    existing_link = re.search(r'https?://\S+', caption)
    if not existing_link:
        await context.bot.send_message(chat_id=chat_id, text="No encontré un link en el mensaje. Reenvía un mensaje de tu canal que tenga el link.")
        return

    link = existing_link.group(0).rstrip(")")
    first_line = caption.splitlines()[0] if caption else ""
    nombre = re.sub(r'https?://\S+', "", first_line).strip()
    nombre = _clean_product_name(nombre)
    if not nombre:
        nombre = "Producto"

    # Obtener URLs de las imágenes desde Telegram CDN
    image_urls = []
    for fid in file_ids:
        try:
            tg_file = await context.bot.get_file(fid)
            image_urls.append(tg_file.file_path)
        except Exception:
            pass

    data_nl = _load_newsletter()
    data_nl[section].append({
        "name": nombre,
        "link": link,
        "image_urls": image_urls,
        "image_url": image_urls[0] if image_urls else "",
        "price": "",
    })
    _save_newsletter(data_nl)
    n = len(data_nl[section])
    img_info = f" ({len(image_urls)} imágenes)" if len(image_urls) > 1 else ""
    await context.bot.send_message(chat_id=chat_id, text=f"✅ Añadido a {section_name} (#{n}){img_info}\n\n{nombre}\n{link}")


async def _handle_newsletter_forwarded(update_or_ctx, context, user_id: int, section: str, file_ids: list, caption: str, bot=None, chat_id: int = None):
    """Procesa un mensaje reenviado de otro canal para la newsletter: detecta links, guarda fotos y pide capturas Hacoo."""
    if bot is None:
        bot = context.bot
    if chat_id is None:
        chat_id = update_or_ctx.message.chat.id

    urls = re.findall(r'https?://\S+', caption)
    urls = [u.rstrip(".,)") for u in urls]
    if not urls:
        await bot.send_message(chat_id=chat_id, text="No encontré ningún link en el mensaje. Reenvía un mensaje con links.")
        return

    # Extraer nombre para cada URL del texto
    if len(urls) == 1:
        first_line = caption.splitlines()[0] if caption else ""
        first_line = re.sub(r'https?://\S+', "", first_line).strip()
        names = [_clean_product_name(first_line) or "Producto"]
    else:
        names = [_clean_product_name(_extract_name_for_url(caption, u)) or f"Producto {i+1}" for i, u in enumerate(urls)]

    user_states[user_id]["nl_original_text"] = caption
    user_states[user_id]["nl_pending_urls"] = urls
    user_states[user_id]["nl_url_index"] = 0
    user_states[user_id]["nl_affiliate_map"] = {}
    user_states[user_id]["nl_names"] = names
    # Detectar si es 1 foto por link o varias fotos para 1 link
    if len(urls) == 1 and len(file_ids) > 1:
        # Todas las fotos son de este único producto
        user_states[user_id]["nl_photo_groups"] = [file_ids]
    elif len(file_ids) == len(urls):
        # 1 foto por link
        user_states[user_id]["nl_photo_groups"] = [[fid] for fid in file_ids]
    else:
        # Número diferente: usar 1 foto por link hasta donde llegue
        user_states[user_id]["nl_photo_groups"] = [[fid] for fid in file_ids] + [[] for _ in range(len(urls) - len(file_ids))]
    user_states[user_id]["state"] = f"newsletter_{section}_waiting_hacoo"

    # Detectar si el mensaje es de Yepex para adaptar el texto
    is_yepex = bool(re.search(r'yepex|yepexpress', caption, re.IGNORECASE))

    n = len(urls)
    nombre_1 = names[0] if names else "primero"
    if is_yepex:
        if n == 1:
            await bot.send_message(chat_id=chat_id, text=f"Es un producto de YepExpress. Envíame tu link de afiliado de '{nombre_1}'.")
        else:
            await bot.send_message(chat_id=chat_id, text=f"Este mensaje tiene {n} productos de YepExpress. Envíame tu link de afiliado del primero: '{nombre_1}' (1/{n}).")
    elif n == 1:
        await bot.send_message(chat_id=chat_id, text=f"Perfecto. Envíame la captura de Hacoo de '{nombre_1}' para generar tu link, o el link directo si es Yepex.")
    else:
        await bot.send_message(chat_id=chat_id, text=f"Este mensaje tiene {n} links. Envíame la captura de Hacoo de '{nombre_1}' (1/{n}), o el link directo si es Yepex.")


async def _handle_newsletter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, section: str):
    """Procesa una foto para la newsletter."""
    section_name = _NEWSLETTER_SECTIONS.get(section, section)
    nl_source = user_states.get(user_id, {}).get("nl_source")

    # Si la fuente no está definida aún, detectar automáticamente
    if not nl_source:
        nl_source = "other"
        user_states[user_id]["nl_source"] = nl_source
        # Foto directa (captura Hacoo): preparar estado waiting_hacoo con sentinel
        if update.message.forward_origin is None:
            user_states[user_id]["nl_pending_urls"] = ["_direct_hacoo"]
            user_states[user_id]["nl_url_index"] = 0
            user_states[user_id]["nl_affiliate_map"] = {}
            user_states[user_id]["nl_names"] = [""]
            user_states[user_id]["nl_photo_groups"] = [[]]
            user_states[user_id]["state"] = f"newsletter_{section}_waiting_hacoo"

    # --- MI CANAL: el caption ya tiene mi link, guardar directamente ---
    if nl_source == "own":
        caption = update.message.caption or ""
        # Si es parte de un álbum y no tiene caption, ignorar (ya se procesó la primera foto)
        if not caption and update.message.media_group_id:
            return
        existing_link = re.search(r'https?://\S+', caption)
        if existing_link:
            link = existing_link.group(0).rstrip(")")
            first_line = caption.splitlines()[0] if caption else ""
            nombre = re.sub(r'https?://\S+', "", first_line).strip()
            nombre = _clean_product_name(nombre)
            if not nombre:
                nombre = "Producto"
            data = _load_newsletter()
            data[section].append({"name": nombre, "link": link, "image_url": "", "price": ""})
            _save_newsletter(data)
            n = len(data[section])
            await update.message.reply_text(f"✅ Añadido a {section_name} (#{n})\n\n{nombre}\n{link}")
            return
        await update.message.reply_text("No encontré un link en el mensaje. Reenvía un mensaje de tu canal que tenga el link.")
        return

    # --- OTRO CANAL: si la foto es REENVIADA → guardar texto y pedir captura ---
    if nl_source == "other" and update.message.forward_origin is not None:
        # Solo procesar el primero del álbum (el que tiene caption con links)
        if user_states[user_id].get("state") == f"newsletter_{section}_waiting_hacoo":
            return  # ignorar fotos reenviadas adicionales del mismo álbum
        caption = update.message.caption or ""
        urls = re.findall(r'https?://\S+', caption)
        urls = [u.rstrip(".,)") for u in urls]
        if not urls:
            await update.message.reply_text("No encontré ningún link en el mensaje. Reenvía un mensaje con links.")
            return
        user_states[user_id]["nl_original_text"] = caption
        user_states[user_id]["nl_pending_urls"] = urls
        user_states[user_id]["nl_url_index"] = 0
        user_states[user_id]["nl_affiliate_map"] = {}
        user_states[user_id]["state"] = f"newsletter_{section}_waiting_hacoo"
        n = len(urls)
        is_yepex = bool(re.search(r'yepex|yepexpress', caption, re.IGNORECASE))
        nombre_1 = user_states[user_id].get("nl_names", [""])[0] if user_states[user_id].get("nl_names") else "primero"
        if is_yepex:
            if n == 1:
                await update.message.reply_text(f"Es un producto de YepExpress. Envíame tu link de afiliado de '{nombre_1}'.")
            else:
                await update.message.reply_text(f"Este mensaje tiene {n} productos de YepExpress. Envíame tu link de afiliado del primero: '{nombre_1}' (1/{n}).")
        elif n == 1:
            await update.message.reply_text("Perfecto. Ahora envíame la captura del producto en Hacoo para generar tu link de afiliado.")
        else:
            await update.message.reply_text(f"Este mensaje tiene {n} links. Envíame la captura de Hacoo del primero (1/{n}).")
        return

    # --- OTRO CANAL: foto DIRECTA (no reenviada) = captura de Hacoo ---
    if nl_source == "other" and user_states[user_id].get("state") == f"newsletter_{section}_waiting_hacoo":
        pending_urls = user_states[user_id].get("nl_pending_urls", [])
        url_index = user_states[user_id].get("nl_url_index", 0)
        affiliate_map = user_states[user_id].get("nl_affiliate_map", {})
        original_text = user_states[user_id].get("nl_original_text", "")
        current_url = pending_urls[url_index] if url_index < len(pending_urls) else None

        if not current_url:
            await update.message.reply_text("Error interno. Usa /newsletter para empezar de nuevo.")
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        status_msg = await update.message.reply_text(f"Generando link {url_index+1}/{len(pending_urls)}...")
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            image_bytes = bytes(await file.download_as_bytearray())

            product_info = gemini_vision(
                image_bytes,
                "Analiza esta captura de la app Hacoo. Devuelve exactamente tres líneas:\n"
                "ID: [solo el número de ID del producto]\n"
                "Precio: [precio redondeado sin decimales con símbolo €]\n"
                "Nombre: [nombre del producto, marca + modelo si es posible]"
            ).strip()

            product_id = ""
            price_raw = ""
            nombre = ""
            for line in product_info.splitlines():
                if line.startswith("ID:"):
                    product_id = line.replace("ID:", "").strip()
                elif line.startswith("Precio:"):
                    price_raw = line.replace("Precio:", "").strip()
                elif line.startswith("Nombre:"):
                    nombre = line.replace("Nombre:", "").strip()

            if not product_id.isdigit():
                await status_msg.edit_text("No encontré el ID en la captura. Envía otra captura de Hacoo.")
                return

            await status_msg.edit_text(f"ID: {product_id} ✓ Generando link {url_index+1}/{len(pending_urls)}...")
            affiliate_link, image_url = await asyncio.gather(
                generate_affiliate_link(product_id),
                asyncio.to_thread(_fetch_og_image_url, product_id),
            )

            # El nombre del mensaje original tiene prioridad sobre el de Gemini
            nl_names = user_states[user_id].get("nl_names", [])
            saved_name = nl_names[url_index] if url_index < len(nl_names) else ""
            if saved_name:
                nombre = _clean_product_name(saved_name)
            elif nombre:
                nombre = _clean_product_name(nombre)
            else:
                nombre = ""

            # Para captura directa (sin URL previa), usar el link generado como clave
            map_key = current_url if current_url != "_direct_hacoo" else affiliate_link
            affiliate_map[map_key] = {"link": affiliate_link, "image_url": image_url or "", "name": nombre, "price": price_raw}
            user_states[user_id]["nl_affiliate_map"] = affiliate_map
            url_index += 1
            user_states[user_id]["nl_url_index"] = url_index

            # ¿Quedan más links?
            if url_index < len(pending_urls):
                user_states[user_id]["state"] = f"newsletter_{section}_waiting_hacoo"
                next_name = nl_names[url_index] if url_index < len(nl_names) else f"producto {url_index+1}"
                original_text = user_states[user_id].get("nl_original_text", "")
                next_is_yepex = bool(re.search(r'yepex|yepexpress', original_text, re.IGNORECASE))
                if next_is_yepex:
                    await status_msg.edit_text(
                        f"✅ Link {url_index}/{len(pending_urls)} generado.\n"
                        f"Envíame tu link de afiliado YepExpress de '{next_name}' ({url_index+1}/{len(pending_urls)})."
                    )
                else:
                    await status_msg.edit_text(
                        f"✅ Link {url_index}/{len(pending_urls)} generado.\n"
                        f"Envíame la captura de Hacoo de '{next_name}' ({url_index+1}/{len(pending_urls)}) o el link directo si es Yepex."
                    )
                return

            # Si es captura directa, pedir nombre y foto antes de guardar
            if current_url == "_direct_hacoo" or map_key == affiliate_link:
                user_states[user_id]["state"] = f"newsletter_{section}_waiting_name_photo"
                user_states[user_id]["nl_direct_link"] = affiliate_link
                user_states[user_id]["nl_direct_image_url"] = image_url or ""
                user_states[user_id]["nl_direct_price"] = price_raw
                user_states[user_id]["nl_direct_name"] = ""
                user_states[user_id]["nl_direct_photos"] = []
                await status_msg.edit_text(
                    f"✅ Link generado: {affiliate_link}\n\n"
                    f"Ahora dime el nombre del producto y envíame la foto (o fotos) para la newsletter.\n"
                    f"Cuando tengas todo, escribe /listo_nl para guardar."
                )
                return

            await status_msg.edit_text("Guardando productos...")
            await _nl_save_all(update.effective_chat.id, user_id, section, affiliate_map, context.bot)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {e}")


async def _handle_newsletter_links(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, section: str):
    """Parsea un mensaje con links directos para la newsletter."""
    text = update.message.text
    url_pattern = r'https?://\S+'
    lines = text.strip().splitlines()

    added = []
    for line in lines:
        url_match = re.search(url_pattern, line)
        if not url_match:
            continue
        link = url_match.group(0)
        # El nombre es todo antes del link, limpiando emojis de ranking
        name_raw = re.sub(url_pattern, "", line).strip()
        name_raw = re.sub(r'^[🥇🥈🥉1-9️⃣\d\.\s\→\-]+', "", name_raw).strip()
        if not name_raw:
            name_raw = "Producto"
        added.append({"name": name_raw, "link": link, "image_url": "", "price": ""})

    if not added:
        await update.message.reply_text("No encontré ningún link en tu mensaje. Envía links con formato `Nombre → https://...`")
        return

    data = _load_newsletter()
    data[section].extend(added)
    _save_newsletter(data)

    section_name = _NEWSLETTER_SECTIONS.get(section, section)
    names = "\n".join(f"• {p['name']}" for p in added)
    await update.message.reply_text(
        f"✅ {len(added)} producto{'s' if len(added)!=1 else ''} añadido{'s' if len(added)!=1 else ''} a *{section_name}*:\n\n{names}\n\n"
        f"Total en {section_name}: {len(data[section])} productos.",
        parse_mode="Markdown",
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set")

    app = Application.builder().token(BOT_TOKEN).post_init(_restore_scheduled_jobs).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getid", cmd_getid))
    app.add_handler(CommandHandler("listo", cmd_listo))
    app.add_handler(CommandHandler("programar", cmd_programar))
    app.add_handler(CommandHandler("pendientes", cmd_pendientes))
    app.add_handler(CommandHandler("backup", cmd_backup))
    app.add_handler(CommandHandler("restore", cmd_restore))
    app.add_handler(CommandHandler("newsletter", cmd_newsletter))
    app.add_handler(CommandHandler("ver_newsletter", cmd_ver_newsletter))
    app.add_handler(CommandHandler("enviar", cmd_enviar_newsletter))
    app.add_handler(CommandHandler("listo_nl", cmd_listo_nl))
    app.add_handler(CallbackQueryHandler(callback_newsletter_section, pattern="^nl_sec_"))
    app.add_handler(CallbackQueryHandler(callback_newsletter_source, pattern="^nl_src_"))
    app.add_handler(CallbackQueryHandler(callback_newsletter_send, pattern="^nl_send_"))
    app.add_handler(MessageHandler(filters.Regex(r"^📋BACKUP\n"), cmd_restore))
    app.add_handler(CommandHandler("cancelar", lambda u, c: (user_states.pop(u.effective_user.id, None), u.message.reply_text("✅ Listo."))))
    app.add_handler(CallbackQueryHandler(callback_calendario, pattern="^cal_"))
    app.add_handler(CallbackQueryHandler(callback_cancel_job, pattern="^cancel_job_"))
    # ── Nuevos handlers canal externo ──
    app.add_handler(CallbackQueryHandler(callback_channel_ok, pattern="^ch_ok_"))
    app.add_handler(CallbackQueryHandler(callback_channel_no, pattern="^ch_no_"))
    app.add_handler(CallbackQueryHandler(callback_channel_publish, pattern="^chpub_"))
    app.add_handler(MessageHandler(filters.PHOTO & filters.FORWARDED, handle_forwarded_channel_msg))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Arrancar Telethon en background junto con el bot
    async def _post_init_with_telethon(application):
        await _restore_scheduled_jobs(application)
        asyncio.create_task(_start_telethon_listener(application))

    app.post_init = _post_init_with_telethon

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
