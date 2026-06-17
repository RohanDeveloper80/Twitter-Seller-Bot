import os, config, qrcode, io
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app_web = Flask(__name__)
# Render will send traffic to this route to keep the bot alive
@app_web.route('/', methods=['POST', 'GET'])
def home(): return "Bot is live!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Buy Accounts", callback_data='buy')],
                [InlineKeyboardButton("📊 Check Stock", callback_data='stock')]]
    await update.message.reply_text("✨ Welcome to Twitter Accounts Store!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'stock':
        await query.edit_message_text("📊 Current Stock: 42 accounts available.")
    elif query.data == 'buy':
        keyboard = [[InlineKeyboardButton("1 Acc (₹20)", callback_data='amt_1')],
                    [InlineKeyboardButton("2 Acc (₹40)", callback_data='amt_2')],
                    [InlineKeyboardButton("4 Acc (₹80)", callback_data='amt_4')],
                    [InlineKeyboardButton("5 Acc (₹100)", callback_data='amt_5')]]
        await query.edit_message_text("🔢 Choose quantity:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('amt_'):
        qty = int(query.data.split('_')[1])
        total = qty * config.PRICE_PER_ACCOUNT
        context.user_data.update({'qty': qty, 'total': total})
        
        upi_url = f"upi://pay?pa={config.UPI_ID}&pn=EliteAscent&am={total}&cu=INR"
        img = qrcode.make(upi_url)
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # Professional caption matching your requested style
        caption = f"💰 Amount to Pay: ₹{total}\nScan this QR. Once paid, click the button below to submit your UTR."
        btn = [[InlineKeyboardButton("📱 Submit Reference No. (UTR)", callback_data='submit_utr')]]
        await query.message.reply_photo(photo=bio, caption=caption, reply_markup=InlineKeyboardMarkup(btn))

async def submit_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("Please reply with your UTR/Reference number.")
    context.user_data['awaiting_utr'] = True

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_utr'):
        utr = update.message.text
        qty = context.user_data.get('qty')
        # User is told to wait, and admin gets the button to approve
        await update.message.reply_text("✅ Payment received! Verification in progress.")
        btn = [[InlineKeyboardButton("✅ Approve Order", callback_data=f'app_{update.effective_user.id}')]]
        await context.bot.send_message(config.ADMIN_ID, f"🔔 New Order\nUser: @{update.effective_user.username}\nQty: {qty}\nUTR: {utr}", reply_markup=InlineKeyboardMarkup(btn))
        context.user_data['awaiting_utr'] = False

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.data.split('_')[1]
    await context.bot.send_message(user_id, "✅ Your payment is verified! Here are your accounts: [ID:PASS]")
    await update.callback_query.edit_message_text("✅ Order Approved and delivered.")

if __name__ == '__main__':
    # Use Webhook to avoid conflicts
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(buy|stock|amt_.*)$'))
    app.add_handler(CallbackQueryHandler(submit_utr, pattern='submit_utr'))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern='^app_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    # Run Flask and Bot
    from threading import Thread
    Thread(target=lambda: app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))).start()
    app.run_polling()
