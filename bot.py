#!/usr/bin/env python3
"""
Telegram Bot - Flood-Safe Auto Upload Videos/PDFs
✅ Features:
- /start → setup remove/add word & channel ID
- Auto upload media sent to bot
- Flood control fully handled (RetryAfter)
- Uploaded media deleted from bot
- Metadata (remove/add word + channel) saved, media not stored
"""

import os
import re
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.error import RetryAfter, TelegramError

# States
ASK_REMOVE, ASK_ADD, ASK_CHANNEL = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- /start -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # If used inside a channel — just show ID
    if chat.type in ["channel", "supergroup"]:
        await update.message.reply_text(
            f"📢 Channel Name: {chat.title}\n🆔 Channel ID: `{chat.id}`"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 नमस्ते! मैं caption से कोई word हटाकर नया word डाल सकता हूँ और media आपके channel पर भेज दूँ।\n\n"
        "सबसे पहले वो word भेजिए जो हटाना है (उदाहरण: @OldName)"
    )
    return ASK_REMOVE

# ---------------- Step 1 -----------------
async def ask_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["remove_word"] = update.message.text.strip()
    await update.message.reply_text("✅ हटाने वाला word मिला!\nअब वो word भेजिए जो उसकी जगह डालना है।")
    return ASK_ADD

# ---------------- Step 2 -----------------
async def ask_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_word"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ जोड़ने वाला word मिला!\nअब वो Channel ID भेजिए जहाँ upload करवाना है।\n\n"
        "👉 Hint: Bot को अपने channel में add करें और वहाँ `/id` चलाएँ ताकि ID मिल सके।"
    )
    return ASK_CHANNEL

# ---------------- Step 3 -----------------
async def ask_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["channel"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ Channel ID सेट हो गई!\nअब आप जितनी चाहें videos या PDFs भेजिए।\n"
        "मैं सबको उसी क्रम में आपके channel पर भेज दूँ।"
    )
    return ConversationHandler.END

# ---------------- Flood-safe send -----------------
async def send_media_safe(context, chat_id, video=None, document=None, caption=""):
    """
    Send media to Telegram channel safely with adaptive flood control
    """
    while True:
        try:
            if video:
                await context.bot.send_video(chat_id=chat_id, video=video, caption=caption)
            elif document:
                await context.bot.send_document(chat_id=chat_id, document=document, caption=caption)
            break  # Success
        except RetryAfter as e:
            wait_time = e.retry_after
            print(f"⚠️ Flood limit reached. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time + 1)  # buffer
        except TelegramError as e:
            print(f"❌ Telegram error: {e}")
            break
        except Exception as e:
            print(f"❌ Unknown error: {e}")
            break

# ---------------- Handle incoming media -----------------
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    remove_word = data.get("remove_word")
    add_word = data.get("add_word")
    channel = data.get("channel")

    if not channel:
        await update.message.reply_text("⚠️ Channel ID not set. Run /start first.")
        return

    caption = update.message.caption or ""
    caption = re.sub(re.escape(remove_word), add_word, caption)

    try:
        if update.message.video:
            await send_media_safe(context, channel, video=update.message.video.file_id, caption=caption)
        elif update.message.document:
            await send_media_safe(context, channel, document=update.message.document.file_id, caption=caption)

        # Delete original media from bot
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading media: {e}")

# ---------------- Channel ID command -----------------
async def channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"📢 Channel Name: {chat.title}\n🆔 Channel ID: `{chat.id}`")

# ---------------- Main -----------------
def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_remove)],
            ASK_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_add)],
            ASK_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_channel)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("id", channel_id))
    # Media handler
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling(allowed_updates=None)  # Polling mode

if __name__ == "__main__":
    main()
