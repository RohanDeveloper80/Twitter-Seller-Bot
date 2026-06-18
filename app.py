import os, config, qrcode, io
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Bot is live!"

# --- Logic: Read and update stock from accounts.txt ---
def get_stock():
    if not os.path.exists('accounts.txt'): return 0
    with open('accounts.txt', 'r') as f: return len(f.readlines())

def get_accounts(qty):
    with open('accounts.txt', 'r') as f: lines = f.readlines()
    if len(lines) < qty: return None
    accounts = [lines[i].strip() for i in range(qty)]
    with open('accounts.txt', 'w') as f: f.writelines(lines[qty:])
    return accounts

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🛒 Buy Accounts", callback_data='buy')],
          [InlineKeyboardButton("📊 Check Stock", callback_data='stock')]]
    await update.message.reply_text("✨ Welcome to Twitter Accounts Store!", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'stock':
        await query.edit_message_text(f"📊 Current Stock: {get_stock()} accounts.")
    
    elif query.data == 'buy':
        kb = [[InlineKeyboardButton(f"{i} Acc (₹{i*20})", callback_data=f'amt_{i}')] for i in [1, 2, 4, 5]]
        await query.edit_message_text("🔢 Choose quantity:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif query.data.startswith('amt_'):
        qty = int(query.data.split('_')[1])
        # Check stock BEFORE asking for money
        if get_stock() < qty:
            await query.edit_message_text("❌ Sorry, not enough stock for that quantity.")
            return
            
        context.user_data.update({'qty': qty})
        upi_url = f"upi://pay?pa={config.UPI_ID}&pn=EliteAscent&am={qty*20}&cu=INR"
        img = qrcode.make(upi_url)
        bio = io.BytesIO(); img.save(bio, 'PNG'); bio.seek(0)
        
        cap = f"💰 Amount to Pay: ₹{qty*20}\nScan this QR. Once paid, click the button below to submit your UTR."
        btn = [[InlineKeyboardButton("📱 Submit Reference No. (UTR)", callback_data='submit_utr')]]
        await query.message.reply_photo(photo=bio, caption=cap, reply_markup=InlineKeyboardMarkup(btn))

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_utr'):
        utr = update.message.text
        if len(utr) != 12 or not utr.isdigit():
            await update.message.reply_text("❌ Invalid UTR. Please send exactly 12 digits.")
            return
        
        qty = context.user_data.get('qty')
        btn = [[InlineKeyboardButton("✅ Approve", callback_data=f'app_{update.effective_user.id}_{qty}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'rej_{update.effective_user.id}')]]
        await context.bot.send_message(config.ADMIN_ID, f"🔔 New Order\nUser: @{update.effective_user.username}\nQty: {qty}\nUTR: {utr}", reply_markup=InlineKeyboardMarkup(btn))
        await update.message.reply_text("✅ PaymentnVerification is in progress please wait.")
        context.user_data['awaiting_utr'] = False

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split('_')
    action, user_id = data[0], data[1]
    
    if action == 'app':
        qty = int(data[2])
        accounts = get_accounts(qty)
        if accounts:
            await context.bot.send_message(user_id, f"✅ Payment verified!\nYour accounts:\n" + "\n".join(accounts))
            await update.callback_query.edit_message_text("✅ Order Approved and delivered.")
        else:
            await update.callback_query.edit_message_text("⚠️ Error: Stock disappeared! Contact support.")
    else:
        await context.bot.send_message(user_id, "❌ Your payment is not confirmed. Please check your UTR or contact support @ZtraxModOwner.")
        await update.callback_query.edit_message_text("❌ Order Rejected.")

if __name__ == '__main__':
    Thread(target=lambda: app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))).start()
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(buy|stock|amt_.*)$'))
    app.add_handler(CallbackQueryHandler(lambda u, c: c.user_data.update({'awaiting_utr': True}) or u.callback_query.message.reply_text("Please reply with your 12-digit UTR:"), pattern='submit_utr'))
    app.add_handler(CallbackQueryHandler(admin_action, pattern='^(app|rej)_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    app.run_polling()
