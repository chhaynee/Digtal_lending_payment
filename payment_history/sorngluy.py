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
    DB_PASSWORD = "Det3181"
    DB_NAME = "demo"
    DB_PORT = 3306
    DB_TIMEOUT = 30

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
                database=Config.DB_NAME,
                port=Config.DB_PORT,
                connection_timeout=Config.DB_TIMEOUT,
                auth_plugin='mysql_native_password'  # Using default auth protocol
            )
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            self.connection = None

    def ensure_connection(self):
        """Ensure database connection is active."""
        try:
            if self.connection is None or not self.connection.is_connected():
                logger.info("Reconnecting to database...")
                self.connect()
        except:
            self.connect()
        return self.connection is not None

def get_user_history(self, userid: str) -> List[Dict]:
    """Get payment history for a specific user."""
    if not self.ensure_connection():
        logger.error("Failed to connect to database")
        return []
        
    try:
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT id, userid, amount, 
                   COALESCE(transaction_date, NOW()) as transaction_date,
                   COALESCE(status, 'completed') as status,
                   COALESCE(payment_method, 'QR code') as payment_method,
                   notes
            FROM users 
            WHERE userid = %s 
            ORDER BY transaction_date DESC
        """
        logger.info(f"Executing query: {query} with userid={userid}")
        cursor.execute(query, (userid,))
        results = cursor.fetchall()
        logger.info(f"Query returned {len(results)} results")
        
        # Format dates for display
        for result in results:
            if 'transaction_date' in result and result['transaction_date']:
                result['transaction_date'] = result['transaction_date'].strftime('%Y-%m-%d %H:%M:%S')
                
        # Log sample of first result if available
        if results:
            logger.info(f"First result: {results[0]}")
        
        cursor.close()
        return results
    except Exception as e:
        logger.error(f"Error retrieving user history: {str(e)}")
        # Print full traceback for debugging
        import traceback
        logger.error(traceback.format_exc())
        return []

    def get_all_users(self) -> List[Dict]:
        """Get all users and their payments."""
        if not self.ensure_connection():
            logger.error("Failed to connect to database")
            return []
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, userid, amount,
                       COALESCE(transaction_date, NOW()) as transaction_date,
                       COALESCE(status, 'completed') as status
                FROM users 
                ORDER BY id DESC 
                LIMIT 5
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            # Format dates for display
            for result in results:
                if 'transaction_date' in result and result['transaction_date']:
                    result['transaction_date'] = result['transaction_date'].strftime('%Y-%m-%d %H:%M:%S')
            
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
            await update.message.reply_text("Please provide a user ID. Example: /history john123")
            return

        userid = context.args[0]
        history = self.db.get_user_history(userid)

        if history:
            message = f"📊 Payment History for {userid}:\n\n"
            total_amount = 0
            for payment in history:
                amount = float(payment.get('amount', 0))
                total_amount += amount
                
                message += (
                    f"🔹 Transaction #{payment['id']}\n"
                    f"💰 Amount: ${amount:.2f}\n"
                    f"🕒 Date: {payment.get('transaction_date', 'N/A')}\n"
                    f"🔄 Status: {payment.get('status', 'completed').title()}\n"
                )
                
                # Add payment method if available
                if 'payment_method' in payment and payment['payment_method']:
                    message += f"💳 Method: {payment['payment_method']}\n"
                
                # Add notes if available
                if 'notes' in payment and payment['notes']:
                    message += f"📝 Note: {payment['notes']}\n"
                
                message += "➖➖➖➖➖➖➖➖\n"
            
            # Add summary
            message += f"\n💵 Total: ${total_amount:.2f} across {len(history)} transactions"
            
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

            # Validate amount
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
        """Handle errors in the bot."""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.message:
            await update.message.reply_text(
                "❌ An error occurred while processing your request. Please try again later."
            )

def main():
    """Start the bot."""
    try:
        # Initialize database schema if needed
        db = PaymentDatabase()
        if db.ensure_connection():
            cursor = db.connection.cursor()
            
            # Check if users table exists, if not create it
            cursor.execute("SHOW TABLES LIKE 'users'")
            if not cursor.fetchone():
                logger.info("Creating users table...")
                cursor.execute("""
                    CREATE TABLE users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        userid VARCHAR(20) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
                        payment_method VARCHAR(50) DEFAULT 'QR code',
                        notes TEXT
                    )
                """)
                cursor.execute("CREATE INDEX idx_userid ON users(userid)")
                db.connection.commit()
                logger.info("Users table created successfully")
            cursor.close()
        
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