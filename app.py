import os
import config
import qrcode
import io
import database

from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

app_web = Flask(__name__)


@app_web.route('/')
def home():
    return "Bot is live!"


# ---------------- USER COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Buy Accounts", callback_data="buy")],
        [InlineKeyboardButton("📊 Check Stock", callback_data="stock")]
    ]

    await update.message.reply_text(
        "✨ Welcome to Twitter Accounts Store!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def ask_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    context.user_data["awaiting_utr"] = True

    await update.callback_query.message.reply_text(
        "📱 Please send your 12-digit UTR number."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "stock":
        await query.edit_message_text(
            f"📊 Current Stock: {database.get_stock()} accounts."
        )

    elif query.data == "buy":

        keyboard = [
            [InlineKeyboardButton(f"{i} Acc (₹{i * 20})", callback_data=f"amt_{i}")]
            for i in [1, 2, 4, 5]
        ]

        await query.edit_message_text(
            "🔢 Choose quantity:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("amt_"):

        qty = int(query.data.split("_")[1])

        if database.get_stock() < qty:
            await query.edit_message_text(
                "❌ Sorry, not enough stock for that quantity."
            )
            return

        context.user_data["qty"] = qty

        upi_url = (
            f"upi://pay?"
            f"pa={config.UPI_ID}"
            f"&pn=EliteAscent"
            f"&am={qty * 20}"
            f"&cu=INR"
        )

        img = qrcode.make(upi_url)

        bio = io.BytesIO()
        img.save(bio, "PNG")
        bio.seek(0)

        caption = (
            f"💰 Amount to Pay: ₹{qty * 20}\n\n"
            f"Scan this QR code.\n"
            f"After payment click the button below and submit your UTR."
        )

        keyboard = [
            [InlineKeyboardButton(
                "📱 Submit Reference No. (UTR)",
                callback_data="submit_utr"
            )]
        ]

        await query.message.reply_photo(
            photo=bio,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------------- PAYMENT HANDLER ----------------

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("awaiting_utr"):
        return

    if context.user_data.get("payment_sent"):
        await update.message.reply_text(
            "⏳ Your payment is already under verification."
        )
        return

    utr = update.message.text.strip()

    if len(utr) != 12 or not utr.isdigit():
        await update.message.reply_text(
            "❌ Invalid UTR. Please send exactly 12 digits."
        )
        return

    qty = context.user_data.get("qty", 1)

    keyboard = [[
        InlineKeyboardButton(
            "✅ Approve",
            callback_data=f"app_{update.effective_user.id}_{qty}"
        ),
        InlineKeyboardButton(
            "❌ Reject",
            callback_data=f"rej_{update.effective_user.id}"
        )
    ]]

    await context.bot.send_message(
        chat_id=config.ADMIN_ID,
        text=(
            f"🔔 NEW ORDER\n\n"
            f"👤 User: @{update.effective_user.username}\n"
            f"🆔 ID: {update.effective_user.id}\n"
            f"📦 Quantity: {qty}\n"
            f"💰 Amount: ₹{qty * 20}\n"
            f"🏦 UTR: {utr}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data["awaiting_utr"] = False
    context.user_data["payment_sent"] = True

    await update.message.reply_text(
        "✅ Payment verification is in progress.\nPlease wait for admin approval."
    )


# ---------------- ADMIN ACTIONS ----------------

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data.split("_")

    action = data[0]
    user_id = int(data[1])

    if action == "app":

        qty = int(data[2])

        accounts = database.get_accounts(qty)

        if accounts:

            await context.bot.send_message(
                user_id,
                "✅ Payment verified!\n\nYour accounts:\n\n"
                + "\n".join(accounts)
            )

            await query.edit_message_text(
                "✅ Order Approved and delivered."
            )

        else:

            await query.edit_message_text(
                "⚠️ Error: No stock available."
            )

    else:

        await context.bot.send_message(
            user_id,
            "❌ Your payment is not confirmed.\nPlease check your UTR or contact support @ZtraxModOwner."
        )

        await query.edit_message_text(
            "❌ Order Rejected."
        )


# ---------------- MAIN ----------------

# ---------------- MAIN ----------------

if __name__ == "__main__":

    Thread(
        target=lambda: app_web.run(
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 8080))
        ),
        daemon=True
    ).start()

    app = Application.builder().token(config.TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern="^(buy|stock|amt_.*)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            ask_utr,
            pattern="submit_utr"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_action,
            pattern="^(app|rej)_"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_payment
        )
    )

    # Remove old webhook before polling
    async def post_init(application):
        await application.bot.delete_webhook(
            drop_pending_updates=True
        )

    app.post_init = post_init

    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )

    app.add_handler(
        CallbackQueryHandler(
            ask_utr,
            pattern="submit_utr"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_action,
            pattern="^(app|rej)_"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_payment
        )
    )

    app.run_polling(
    drop_pending_updates=True,
    allowed_updates=Update.ALL_TYPES
)
