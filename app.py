from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Buy Accounts", callback_data='buy')],
                [InlineKeyboardButton("📊 Check Stock", callback_data='stock')]]
    await update.message.reply_text(
        "✨ *Welcome to Elite Accounts!*\n\nWe provide the highest quality Twitter accounts. Please choose an option below:",
        parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'stock':
        await query.edit_message_text("📊 Current Stock: 42 Twitter accounts available.")
    
    elif query.data == 'buy':
        keyboard = [[InlineKeyboardButton("1 Account (₹20)", callback_data='amt_1')],
                    [InlineKeyboardButton("2 Accounts (₹40)", callback_data='amt_2')],
                    [InlineKeyboardButton("5 Accounts (₹100)", callback_data='amt_5')]]
        await query.edit_message_text("🔢 How many accounts do you need?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('amt_'):
        qty = int(query.data.split('_')[1])
        total = qty * config.PRICE_PER_ACCOUNT
        context.user_data.update({'qty': qty, 'total': total})
        
        # Payment URL
        upi_link = f"upi://pay?pa={config.UPI_ID}&pn=EliteAscent&am={total}&cu=INR"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_link}"
        
        await query.edit_message_text(f"💳 *Payment Details*\nAmount: ₹{total}\nUPI ID: `{config.UPI_ID}`\n\nPlease pay and send your UTR/Reference number.", parse_mode='Markdown')
        await query.message.reply_photo(photo=qr_url, caption="Scan this QR to pay.")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    utr = update.message.text
    qty = context.user_data.get('qty')
    if not qty: return await update.message.reply_text("Please start your order with /buy.")

    await update.message.reply_text("⏳ *Payment received!* Your transaction is being verified.", parse_mode='Markdown')
    
    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f'app_{update.effective_user.id}'),
                 InlineKeyboardButton("❌ Reject", callback_data=f'rej_{update.effective_user.id}')]]
    await context.bot.send_message(config.ADMIN_ID, f"🔔 *New Order Verification*\nUser: @{update.effective_user.username}\nQty: {qty}\nUTR: {utr}", 
                                   parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    app.run_polling()
