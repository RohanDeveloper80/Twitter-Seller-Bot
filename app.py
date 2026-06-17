import os, config, qrcode, io
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Bot is live!"

# --- Account Management Helper ---
def get_and_remove_account(qty):
    try:
        with open('accounts.txt', 'r') as f: lines = f.readlines()
        if len(lines) < qty: return None
        accounts = [lines[i].strip() for i in range(qty)]
        with open('accounts.txt', 'w') as f: f.writelines(lines[qty:])
        return accounts
    except: return None

def get_stock():
    try:
        with open('accounts.txt', 'r') as f: return len(f.readlines())
    except: return 0

# --- Bot Logic ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🛒 Buy", callback_data='buy')], [InlineKeyboardButton("📊 Stock", callback_data='stock')]]
    await update.message.reply_text("✨ Welcome to Elite Accounts!", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data == 'stock':
        await query.edit_message_text(f"📊 Available Stock: {get_stock()} accounts.")
    elif query.data == 'buy':
        kb = [[InlineKeyboardButton(f"{i} Acc (₹{i*20})", callback_data=f'amt_{i}')] for i in [1, 2, 4, 5]]
        await query.edit_message_text("🔢 Select quantity:", reply_markup=InlineKeyboardMarkup(kb))
    elif query.data.startswith('amt_'):
        qty = int(query.data.split('_')[1])
        context.user_data.update({'qty': qty})
        upi = f"upi://pay?pa={config.UPI_ID}&pn=EliteAscent&am={qty*20}&cu=INR"
        img = qrcode.make(upi); bio = io.BytesIO(); img.save(bio, 'PNG'); bio.seek(0)
        btn = [[InlineKeyboardButton("📱 Submit 12-digit UTR", callback_data='submit_utr')]]
        await query.message.reply_photo(photo=bio, caption=f"💰 Pay ₹{qty*20}\nSubmit UTR below.", reply_markup=InlineKeyboardMarkup(btn))

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_utr'):
        utr = update.message.text
        if len(utr) != 12 or not utr.isdigit():
            await update.message.reply_text("❌ Send a valid 12-digit UTR."); return
        qty = context.user_data.get('qty')
        btn = [[InlineKeyboardButton("✅ Approve", callback_data=f'app_{update.effective_user.id}_{qty}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'rej_{update.effective_user.id}')]]
        await context.bot.send_message(config.ADMIN_ID, f"🔔 Order: @{update.effective_user.username}\nQty: {qty}\nUTR: {utr}", reply_markup=InlineKeyboardMarkup(btn))
        await update.message.reply_text("✅ UTR received. Verifying..."); context.user_data['awaiting_utr'] = False

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split('_'); action, user_id = data[0], data[1]
    if action == 'app':
        accounts = get_and_remove_account(int(data[2]))
        if accounts:
            await context.bot.send_message(user_id, f"✅ Verified! Accounts:\n" + "\n".join(accounts))
            await update.callback_query.edit_message_text("✅ Order Delivered.")
        else:
            await context.bot.send_message(user_id, "⚠️ Stock error. Contact support."); await update.callback_query.edit_message_text("⚠️ Out of stock.")
    else:
        await context.bot.send_message(user_id, "❌ Rejected. Please send correct UTR or contact @ZtraxModOwner.")
        await update.callback_query.edit_message_text("❌ Order Rejected.")

if __name__ == '__main__':
    from threading import Thread
    Thread(target=lambda: app_web.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))).start()
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(buy|stock|amt_.*)$'))
    app.add_handler(CallbackQueryHandler(lambda u, c: c.user_data.update({'awaiting_utr': True}) or u.callback_query.message.reply_text("Send 12-digit UTR:"), pattern='submit_utr'))
    app.add_handler(CallbackQueryHandler(admin_action, pattern='^(app|rej)_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    app.run_polling()
