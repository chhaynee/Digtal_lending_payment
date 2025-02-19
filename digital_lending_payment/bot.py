from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from config import Config, logger
from database import PaymentDatabase
from qr_generator import PaymentQRGenerator

class PaymentBot:
    def __init__(self):
        self.qr_generator = PaymentQRGenerator()
        self.db = PaymentDatabase()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = (
            "🤖 Welcome to the Digital Lending Payment Bot!\n\n"
            "Commands:\n"
            "/qr <user_id> <amount> - Generate a payment QR code\n"
            "/history <user_id> - View payment history\n"
            "/recent - View recent payments\n"
            "/help - Show this help message\n"
            "/status - Check bot status"
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.start_command(update, context)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        db_status = "✅ Online" if self.db.ensure_connection() else "❌ Offline"
        status_message = (
            "✅ Bot is running normally\n"
            f"🕒 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🗄️ Database: {db_status}\n"
            "🔄 QR Service: Online"
        )
        await update.message.reply_text(status_message)

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /history command."""
        if not context.args:
            await update.message.reply_text("Please provide a user ID. Example: /history pong")
            return


        userid = context.args[0]
        history = self.db.get_user_history(userid)

        if history:
            message = f"📊 Payment History for {userid}:\n\n"
            total_amount = 0
            
            for payment in history:
                amount = float(payment['amount'])
                total_amount += amount
                
                message += (
                    f"🔹 Transaction #{payment['id']}\n"
                    f"💰 Amount: ${amount:.2f}\n"
                    f"➖➖➖➖➖➖➖➖\n"
                )
            
            message += f"\n💵 Total: ${total_amount:.2f} across {len(history)} transactions"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(f"❌ No payment history found for {userid}")


    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        recent_payments = self.db.get_all_users()
        
        if recent_payments:
            message = "📊 Recent Payments:\n\n"
            for payment in recent_payments:
                message += (
                    f"🔹 Transaction #{payment['id']}\n"
                    f"👤 User ID: {payment['userid']}\n"
                    f"💰 Amount: ${float(payment['amount']):.2f}\n"
                    f"🕒 Date: {payment.get('transaction_date', 'N/A')}\n"
                    f"🔄 Status: {payment.get('status', 'completed').title()}\n"
                    f"➖➖➖➖➖➖➖➖\n"
                )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ No recent payments found")

    async def create_qr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if len(context.args) != 2:
                await update.message.reply_text(
                    "⚠️ Invalid format! Use: /qr <user_id> <amount>\n"
                    "Example: /qr user123 50.50"
                )
                return

            user_id, amount = context.args

            if not self.qr_generator.validate_user_id(user_id):
                await update.message.reply_text(
                    "❌ Invalid user ID format! User ID should be 4-20 characters "
                    "and contain only letters, numbers, underscores, or hyphens."
                )
                return

            try:
                amount_float = float(amount)
                if amount_float <= 0 or amount_float > Config.MAX_AMOUNT:
                    await update.message.reply_text(
                        f"❌ Invalid amount! Amount should be between 0 and {Config.MAX_AMOUNT}."
                    )
                    return
            except ValueError:
                await update.message.reply_text("❌ Invalid amount! Please enter a valid number.")
                return

            payment_info = f"{Config.PAYMENT_BASE_URL}?user={user_id}&amount={amount}"
            await update.message.reply_text("🔄 Generating QR code...")
            qr_image = self.qr_generator.generate_qr_code(payment_info)
            
            if qr_image:
                logger.info(f"Generated QR code for user {user_id} with amount {amount}")
                await update.message.reply_photo(
                    photo=InputFile(qr_image, filename="payment_qr.png"),
                    caption=(
                        f"💳 Payment QR Code\n"
                        f"👤 User ID: {user_id}\n"
                        f"💰 Amount: ${amount}\n"
                        f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                )
            else:
                await update.message.reply_text("❌ Failed to generate QR code. Please try again later.")
                
        except Exception as e:
            logger.error(f"Error in create_qr_command: {str(e)}")
            await update.message.reply_text("❌ An error occurred. Please try again later.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.message:
            await update.message.reply_text(
                "❌ An error occurred while processing your request. Please try again later."
            )