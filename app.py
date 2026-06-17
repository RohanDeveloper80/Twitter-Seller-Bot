import os, config, qrcode, io
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Keep-Alive Server for Render ---
app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Bot is running!"
def run(): app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Buy Accounts", callback_data='buy')],
                [InlineKeyboardButton("📊 Check Stock", callback_data='stock')]]
    await update.message.reply_text("✨ Welcome to Elite Accounts!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'stock':
        await query.edit_message_text("📊 Current Stock: 42 Twitter accounts available.")
    elif query.data == 'buy':
        keyboard = [[InlineKeyboardButton("1 Acc (₹20)", callback_data='amt_1')],
                    [InlineKeyboardButton("2 Acc (₹40)", callback_data='amt_2')]]
        await query.edit_message_text("🔢 Choose quantity:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('amt_'):
        qty = int(query.data.split('_')[1])
        total = qty * config.PRICE_PER_ACCOUNT
        context.user_data.update({'qty': qty, 'total': total})
        
        # Professional UPI QR with exact amount
        upi_url = f"upi://pay?pa={config.UPI_ID}&pn=EliteAscent&am={total}&cu=INR"
        img = qrcode.make(upi_url)
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        btn = [[InlineKeyboardButton("📱 Submit Reference No. (UTR)", callback_data='submit_utr')]]
        await query.message.reply_photo(photo=bio, caption=f"💰 Amount: ₹{total}\nScan to pay.", reply_markup=InlineKeyboardMarkup(btn))

async def submit_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("Please reply with your UTR/Reference number.")
    context.user_data['awaiting_utr'] = True

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_utr'):
        utr = update.message.text
        qty = context.user_data.get('qty')
        await update.message.reply_text("✅ Payment received! Verification in progress.")
        await context.bot.send_message(config.ADMIN_ID, f"🔔 New Order\nUser: @{update.effective_user.username}\nQty: {qty}\nUTR: {utr}")
        context.user_data['awaiting_utr'] = False

if __name__ == '__main__':
    Thread(target=run).start()
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(buy|stock|amt_.*)$'))
    app.add_handler(CallbackQueryHandler(submit_utr, pattern='submit_utr'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    app.run_polling()
