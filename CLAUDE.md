# TrentBot — Referencia estable

## Rama de trabajo
- Rama principal: `main`
- Rama de desarrollo actual: `claude/fix-hacoo-api-sign-xxSTy`

## Commit estable de referencia
`499017e` — "perf: eliminar chat general con Gemini para reducir consumo de API"

## Descripción del bot
Bot de Telegram para generar posts de afiliado de Hacoo. El usuario envía una
captura de pantalla de la app Hacoo, el bot extrae el ID del producto, genera
el link de afiliado con Playwright, detecta la marca/nombre desde la imagen del
producto en alta resolución, y compone el mensaje final listo para enviar al canal.

## Flujo principal (handle_photo)
1. Usuario envía captura de la app Hacoo
2. Gemini Vision extrae: ID del producto, precio, número de colores
3. Se descarga la imagen principal del producto desde `hacoo.pl/en-ES/detail/{id}` (og:image)
4. Gemini Vision analiza esa imagen de alta resolución → detecta Marca y Nombre
5. Se genera el link de afiliado con Playwright
6. Si se detectó marca/nombre: muestra el título auto-detectado y pide fotos
7. Si no: pide al usuario que escriba el título manualmente
8. Usuario envía fotos del producto
9. Bot compone el mensaje y lo envía. Estado pasa a "editing".
10. Usuario puede modificar el texto con instrucciones en lenguaje natural (Gemini),
    usar /programar para programarlo, o /cancelar.

## Formato del mensaje
```
{título} —> {precio}💎
{N colores} 🎨

{link de afiliado}
```

## Scheduling (APScheduler via job_queue)
- Los jobs se persisten en `/tmp/scheduled_jobs.json`
- Al reiniciar el bot, `_restore_scheduled_jobs` (post_init hook) restaura los jobs futuros
- `/backup`: bot envía JSON de todos los jobs pendientes
- `/restore` (o reenviar mensaje de backup): reprograma los jobs tras un deploy

## Gemini
- Modelo principal: `gemini-2.5-flash`
- Solo se usa para: análisis de capturas, análisis de imagen de producto, edición de mensajes
- NO hay chat general (eliminado para ahorrar tokens)
- Límite: 5 RPM — el código maneja 429 con reintentos

## Variables de entorno necesarias
- `BOT_TOKEN` — token del bot de Telegram
- `GEMINI_API_KEY` — API key de Gemini
- `CHANNEL_ID` — ID del canal donde se envían los posts
- `HACOO_EMAIL` — email para login en Hacoo
- `HACOO_PASSWORD` — contraseña para login en Hacoo

## Archivos clave
- `bot.py` — todo el código del bot
- `requirements.txt` — dependencias
- `/tmp/scheduled_jobs.json` — jobs persistidos (se borra en deploy de Railway)

## Comandos disponibles
- `/backup` — exporta jobs pendientes como JSON
- `/restore` — importa jobs de un backup (o reenviar el mensaje de backup)
- `/pendientes` — lista los mensajes programados
- `/cancelar` — cancela la edición actual
- `/programar` — programa el mensaje actual para una hora
- `/listo` — fuerza composición si hay fotos en buffer
