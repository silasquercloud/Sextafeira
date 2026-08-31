import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AGNES_KEY = os.getenv("AGNES_KEY")

AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
MODEL = "agnes-2.5-flash"


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.post(
            AGNES_URL,
            headers={
                "Authorization": f"Bearer {AGNES_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": update.message.text
                    }
                ]
            },
            timeout=60
        )

        data = response.json()

        if response.status_code != 200:
            await update.message.reply_text(
                f"Erro na API: {data}"
            )
            return

        answer = data["choices"][0]["message"]["content"]

        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(
            f"Erro: {e}"
        )


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, chat)
)

print("Bot iniciado!")

app.run_polling()
