import os, config, qrcode, io
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Bot is live!"

# Helper: Read Stock
def get_stock():
    with open('stock.txt', 'r') as f: return int(f.read().strip())

# Helper: Update Stock
def update_stock(qty):
    current = get_stock()
    with open('stock.txt', 'w') as f: f.write(str(current - qty))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🛒 Buy Accounts", callback_data='buy')],
          [InlineKeyboardButton("📊 Check Stock", callback_data='stock')]]
    await update.message.reply_text("✨ Welcome to Twitter Accounts Store!", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'stock':
        await query.edit_message_text(f"📊 Available Stock: {get_stock()} accounts.")
    elif query.data == 'buy':
        kb = [[InlineKeyboardButton(f"{i} Acc (₹{i*20})", callback_data=f'amt_{i}')] for i in [1, 2, 4, 5]]
        await query.edit_message_text("🔢 Select quantity:", reply_markup=InlineKeyboardMarkup(kb))
    elif query.data.startswith('amt_'):
        qty = int(query.data.split('_')[1])
        context.user_data.update({'qty': qty})
        
        upi_url = f"upi://pay?pa={config.UPI_ID}&pn=EliteAscent&am={qty*20}&cu=INR"
        img = qrcode.make(upi_url)
        bio = io.BytesIO()
        img.save(bio, 'PNG'); bio.seek(0)
        
        cap = f"💰 Pay ₹{qty*20}\nScan QR. After payment, click below to submit UTR.\n\n🆔 Order Ref: TXN{update.effective_user.id}\nℹ️ Need Help? Contact @ZtraxModOwner"
        btn = [[InlineKeyboardButton("📱 Submit UTR", callback_data='submit_utr')]]
        await query.message.reply_photo(photo=bio, caption=cap, reply_markup=InlineKeyboardMarkup(btn))

async def submit_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("Reply with your UTR/Reference number:")
    context.user_data['awaiting_utr'] = True

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_utr'):
        utr = update.message.text
        qty = context.user_data.get('qty')
        # Send to YOU (Admin)
        btn = [[InlineKeyboardButton("✅ Approve & Deliver", callback_data=f'app_{update.effective_user.id}_{qty}')]]
        await context.bot.send_message(config.ADMIN_ID, f"🔔 New Order!\nCustomer: @{update.effective_user.username}\nQty: {qty}\nUTR: {utr}", reply_markup=InlineKeyboardMarkup(btn))
        await update.message.reply_text("✅ Payment received! Verification in progress.")
        context.user_data['awaiting_utr'] = False

async def approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split('_')
    user_id, qty = data[1], int(data[2])
    
    # Logic: Deliver and Update Stock
    update_stock(qty)
    await context.bot.send_message(user_id, "✅ Payment Verified! Your accounts: [ID:PASS]")
    await update.callback_query.edit_message_text("✅ Order Approved and Delivered.")

if __name__ == '__main__':
    Thread(target=lambda: app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))).start()
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(buy|stock|amt_.*)$'))
    app.add_handler(CallbackQueryHandler(submit_utr, pattern='submit_utr'))
    app.add_handler(CallbackQueryHandler(approve_order, pattern='^app_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    app.run_polling()
