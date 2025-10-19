#!/usr/bin/env python3
"""
Telegram Bot (Auto Channel ID Detection)
✅ Features:
- If /start used in channel → auto send channel ID
- If /start used in DM → normal caption edit setup
- Replace word in caption & upload to selected channel
"""

import os
import re
import logging
from telegram import Update, Chat
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

ASK_REMOVE, ASK_ADD, ASK_CHANNEL, ASK_MEDIA = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # if started inside a channel
    if chat.type in ["channel", "supergroup"]:
        await update.message.reply_text(
            f"📢 Channel Name: {chat.title}\n🆔 Channel ID: `{chat.id}`\n\n"
            "अब इस Channel ID को अपने private chat में भेज दो जहाँ तुमने /start किया था।"
        )
        return ConversationHandler.END

    # if started in private chat
    await update.message.reply_text(
        "👋 नमस्ते! मैं caption से कोई word हटाकर नया word डाल सकता हूँ और वही फ़ाइल आपके channel पर भेज दूँ।\n\n"
        "सबसे पहले वो word भेजिए जो हटाना है (उदाहरण: @RexodasEmpire)"
    )
    return ASK_REMOVE


# --- ASK REMOVE WORD ---
async def ask_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["remove_word"] = update.message.text.strip()
    await update.message.reply_text("✅ हटाने वाला word मिला!\nअब वो word भेजिए जो उसकी जगह डालना है।")
    return ASK_ADD


# --- ASK ADD WORD ---
async def ask_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_word"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ जोड़ने वाला word मिला!\nअब वो Channel ID भेजिए जहाँ upload करवाना है।\n\n"
        "👉 Hint: Bot को अपने channel में add करें और वहाँ `/start` चलाएँ ताकि ID मिल सके।"
    )
    return ASK_CHANNEL


# --- ASK CHANNEL ID ---
async def ask_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["channel"] = update.message.text.strip()
    await update.message.reply_text("✅ Channel ID सेट हो गई!\nअब वो video या PDF भेजिए जिसमें caption है।")
    return ASK_MEDIA


# --- PROCESS MEDIA ---
async def ask_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    remove_word = data.get("remove_word")
    add_word = data.get("add_word")
    channel = data.get("channel")

    caption = update.message.caption or ""
    new_caption = re.sub(re.escape(remove_word), add_word, caption)

    try:
        if update.message.video:
            await context.bot.send_video(
                chat_id=channel,
                video=update.message.video.file_id,
                caption=new_caption,
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=channel,
                document=update.message.document.file_id,
                caption=new_caption,
            )
        await update.message.reply_text("✅ File सफलतापूर्वक भेज दी गई!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

    return ConversationHandler.END


# --- MAIN FUNCTION ---
def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_remove)],
            ASK_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_add)],
            ASK_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_channel)],
            ASK_MEDIA: [MessageHandler((filters.VIDEO | filters.Document.ALL), ask_media)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()
