import os
import re
import logging
import requests
import mysql.connector
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict
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
    MAX_AMOUNT = 10000
    PAYMENT_BASE_URL = "https://pay.ababank.com/yqH27C1mLesTLrFaA"
    
    # Database configuration
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "payment_database"

class PaymentDatabase:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """Connect to MySQL database."""
        try:
            self.connection = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            self.connection = None

    def get_user_history(self, userid: str) -> List[Dict]:
        """Get payment history for a specific user."""
        if not self.connection:
            self.connect()
            
        if not self.connection:
            return []
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE userid = %s", (userid,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error retrieving user history: {str(e)}")
            return []

    def get_all_users(self) -> List[Dict]:
        """Get all users and their payments."""
        if not self.connection:
            self.connect()
            
        if not self.connection:
            return []
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 5")
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            return []

class PaymentQRGenerator:
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format."""
        return bool(re.match(r'^[A-Za-z0-9_-]{4,20}$', user_id))
    
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
        self.db = PaymentDatabase()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
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
        """Handle the /help command."""
        await self.start_command(update, context)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command."""
        db_status = "✅ Online" if self.db.connection else "❌ Offline"
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
            await update.message.reply_text("Please provide a user ID. Example: /history john123")
            return

        userid = context.args[0]
        history = self.db.get_user_history(userid)

        if history:
            message = f"📊 Payment History for {userid}:\n\n"
            for payment in history:
                message += (
                    f"💰 Amount: ${payment['amount']}\n"
                    f"🆔 Transaction ID: {payment['id']}\n"
                    f"➖➖➖➖➖➖➖➖\n"
                )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(f"❌ No payment history found for {userid}")

    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /recent command."""
        recent_payments = self.db.get_all_users()
        
        if recent_payments:
            message = "📊 Recent Payments:\n\n"
            for payment in recent_payments:
                message += (
                    f"👤 User ID: {payment['userid']}\n"
                    f"💰 Amount: ${payment['amount']}\n"
                    f"➖➖➖➖➖➖➖➖\n"
                )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ No recent payments found")

    async def create_qr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /qr command."""
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
        """Handle errors in the bot."""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.message:
            await update.message.reply_text(
                "❌ An error occurred while processing your request. Please try again later."
            )

def main():
    """Start the bot."""
    try:
        bot = PaymentBot()
        application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("help", bot.help_command))
        application.add_handler(CommandHandler("status", bot.status_command))
        application.add_handler(CommandHandler("qr", bot.create_qr_command))
        application.add_handler(CommandHandler("history", bot.history_command))
        application.add_handler(CommandHandler("recent", bot.recent_command))
        
        # Add error handler
        application.add_error_handler(bot.error_handler)
        
        logger.info("Bot started successfully")
        print("🤖 Bot is running...")
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        raise

if __name__ == "__main__":
    main()