import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

client = Anthropic(api_key=ANTHROPIC_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\u00a1Hola! Soy TrentBot, impulsado por Claude AI. \u00bfEn qu\u00e9 puedo ayudarte?"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Env\u00edame cualquier mensaje y te responder\u00e9 con la ayuda de Claude AI.\n"
        "Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/help - Ver este mensaje de ayuda"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Message from {user.first_name} (@{user.username}): {user_message}")

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": user_message}
            ]
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

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TrentBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
