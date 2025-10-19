#!/usr/bin/env python3
"""
Telegram Bot - Multi File + Channel ID + Caption Replace
✅ Features:
- /start in DM → setup remove/add word & channel
- /id in channel → show channel id automatically (even if no reply possible)
- Accepts multiple videos or PDFs (up to 100)
- Sends to channel in same order as received
"""

import os
import re
import logging
from telegram import Update
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

# ---------------- /start -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # If used inside a channel — just show ID
    if chat.type in ["channel", "supergroup"]:
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"📢 Channel Name: {chat.title}\n🆔 Channel ID: `{chat.id}`",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 नमस्ते! मैं caption से कोई word हटाकर नया word डाल सकता हूँ और वही फ़ाइल आपके channel पर भेज दूँ।\n\n"
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
    context.user_data["queue"] = []
    await update.message.reply_text(
        "✅ Channel ID सेट हो गई!\nअब आप जितनी चाहें videos या PDFs (100 तक) भेजिए।\n"
        "मैं सबको उसी क्रम में आपके channel पर भेज दूँ।"
    )
    return ASK_MEDIA


# ---------------- Step 4: Collect media -----------------
async def collect_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    queue = data.get("queue", [])

    # store media info
    media_item = {
        "video": update.message.video.file_id if update.message.video else None,
        "document": update.message.document.file_id if update.message.document else None,
        "caption": update.message.caption or ""
    }

    queue.append(media_item)
    context.user_data["queue"] = queue

    await update.message.reply_text(f"📦 जोड़ा गया ({len(queue)} files total)\n"
                                    "जब सब भेज दो, तब /upload लिखो।")
    return ASK_MEDIA


# ---------------- Step 5: Upload all -----------------
async def upload_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    queue = data.get("queue", [])
    remove_word = data.get("remove_word", "")
    add_word = data.get("add_word", "")
    channel = data.get("channel", "")

    if not queue:
        await update.message.reply_text("⚠️ कोई video या PDF नहीं मिली।")
        return ASK_MEDIA

    await update.message.reply_text(f"🚀 Upload शुरू — {len(queue)} files भेजी जा रही हैं...")

    count = 0
    for item in queue:
        caption = re.sub(re.escape(remove_word), add_word, item["caption"])
        try:
            if item["video"]:
                await context.bot.send_video(chat_id=channel, video=item["video"], caption=caption)
            elif item["document"]:
                await context.bot.send_document(chat_id=channel, document=item["document"], caption=caption)
            count += 1
        except Exception as e:
            await update.message.reply_text(f"❌ Error on file {count+1}: {e}")

    await update.message.reply_text(f"✅ Upload पूरा! {count}/{len(queue)} files भेज दी गईं।")
    data["queue"].clear()
    return ConversationHandler.END


# ---------------- Channel ID command -----------------
async def channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"📢 Channel Name: {chat.title}\n🆔 Channel ID: `{chat.id}`",
            parse_mode="Markdown"
        )
    except Exception:
        # If message is None (in channel post), send via bot directly
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"🆔 Channel ID: `{chat.id}`",
            parse_mode="Markdown"
        )


# ---------------- MAIN -----------------
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not found in environment variables!")

    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_remove)],
            ASK_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_add)],
            ASK_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_channel)],
            ASK_MEDIA: [
                MessageHandler(filters.VIDEO | filters.Document.ALL, collect_media),
                CommandHandler("upload", upload_all),
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("id", channel_id))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
