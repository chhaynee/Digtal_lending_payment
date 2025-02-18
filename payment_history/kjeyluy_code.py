import decimal
import os
import re
import logging
import requests
from decimal import Decimal
from datetime import datetime
from typing import Optional
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    TELEGRAM_BOT_TOKEN = "7746794164:AAGWR56zZk1xlTK3kp7Ta0vKJw5mim85a4U"
    GOQR_API_URL = "https://api.qrserver.com/v1/create-qr-code/"
    QR_CODE_SIZE = "300x300"
    MAX_AMOUNT = 10000  # Maximum payment amount
    PAYMENT_BASE_URL = "https://pay.ababank.com/1vk4LAyFyTa5Z46E7"
    
class PaymentQRGenerator:
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format."""
        return bool(re.match(r'^[A-Za-z0-9_-]{4,20}$', user_id))
    
    @staticmethod
    def validate_amount(amount: str) -> bool:
        """Validate payment amount."""
        try:
            amount_decimal = Decimal(amount)
            return 0 < amount_decimal <= Config.MAX_AMOUNT
        except (ValueError, decimal.InvalidOperation):
            return False
    
    @staticmethod
    def generate_qr_code(payment_data: str) -> Optional[BytesIO]:
        """Generate QR code for payment data."""
        try:
            params = {
                "data": payment_data,
                "size": Config.QR_CODE_SIZE,
                "format": "png"
            }
            response = requests.get(Config.GOQR_API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            qr_image = BytesIO(response.content)
            qr_image.seek(0)
            return qr_image
            
        except requests.exceptions.RequestException as e:
            logger.error(f"QR code generation failed: {str(e)}")
            return None

class PaymentBot:
    def __init__(self):
        self.qr_generator = PaymentQRGenerator()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            "🤖 Welcome to the Digital Lending Payment Bot!\n\n"
            "Commands:\n"
            "/qr <user_id> <amount> - Generate a payment QR code\n"
            "/help - Show this help message\n"
            "/status - Check bot status"
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        await self.start_command(update, context)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command."""
        status_message = (
            "✅ Bot is running normally\n"
            f"🕒 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "🔄 QR Service: Online"
        )
        await update.message.reply_text(status_message)

    async def create_qr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /qr command."""
        try:
            # Check arguments
            if len(context.args) != 2:
                await update.message.reply_text(
                    "⚠️ Invalid format! Use: /qr <user_id> <amount>\n"
                    "Example: /qr user123 50.50"
                )
                return

            user_id, amount = context.args

            # Validate inputs
            if not self.qr_generator.validate_user_id(user_id):
                await update.message.reply_text(
                    "❌ Invalid user ID format! User ID should be 4-20 characters "
                    "and contain only letters, numbers, underscores, or hyphens."
                )
                return

            if not self.qr_generator.validate_amount(amount):
                await update.message.reply_text(
                    f"❌ Invalid amount! Amount should be between 0 and {Config.MAX_AMOUNT}"
                )
                return

            # Generate payment URL
            payment_info = f"{Config.PAYMENT_BASE_URL}?user={user_id}&amount={amount}"
            
            # Generate QR code
            await update.message.reply_text("🔄 Generating QR code...")
            qr_image = self.qr_generator.generate_qr_code(payment_info)
            
            if qr_image:
                # Log successful generation
                logger.info(f"Generated QR code for user {user_id} with amount {amount}")
                
                # Send QR code with payment details
                await update.message.reply_photo(
                    photo=InputFile(qr_image, filename="payment_qr.png"),
                    caption=(
                        f"💳 Payment QR Code\n"
                        f"👤 User ID: {user_id}\n"
                        f"💰 Amount: ${amount}\n"
                        f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"🔗 PaymentLink:{payment_info}\n"
                        f"➖➖➖➖➖➖➖➖\n"
                    )
                )
            else:
                await update.message.reply_text("❌ Failed to generate QR code. Please try again later.")
                
        except Exception as e:
            logger.error(f"Error in create_qr_command: {str(e)}")
            await update.message.reply_text("❌ An error occurred. Please try again later.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the bot."""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.message:
            await update.message.reply_text(
                "❌ An error occurred while processing your request. Please try again later."
            )

def main():
    """Start the bot."""
    try:
        # Initialize bot
        bot = PaymentBot()
        application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("help", bot.help_command))
        application.add_handler(CommandHandler("status", bot.status_command))
        application.add_handler(CommandHandler("qr", bot.create_qr_command))
        
        # Add error handler
        application.add_error_handler(bot.error_handler)
        
        # Start the bot
        logger.info("Bot started successfully")
        print("🤖 Bot is running...")
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        raise

if __name__ == "__main__":
    main()