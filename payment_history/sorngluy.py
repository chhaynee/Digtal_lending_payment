import os
import re
import logging
import requests
from openpyxl import load_workbook
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
    EXCEL_PATH = r"C:\Users\LENOVO\Documents\DigitLending\Digtal_lending_payment\payment_history\payment_history.xlsx"

class PaymentHistory:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.payment_records = []
        self.load_data()

    def load_data(self):
        """Load data from Excel file using openpyxl."""
        try:
            # Load the workbook
            wb = load_workbook(self.file_path)
            # Get the active sheet
            sheet = wb.active
            
            # Get all values from the first row
            data_list = []
            for cell in sheet[1]:
                if cell.value is not None:
                    data_list.append(str(cell.value))
            
            # Process data in pairs (customer_name and amount)
            for i in range(0, len(data_list), 2):
                if i + 1 < len(data_list):
                    try:
                        record = {
                            'customer_name': data_list[i],
                            'amount': float(data_list[i + 1]),
                            'date': datetime.now().strftime('%Y-%m-%d')
                        }
                        self.payment_records.append(record)
                    except ValueError:
                        logger.error(f"Error converting amount for customer {data_list[i]}")
                        continue
            
            logger.info(f"Successfully loaded {len(self.payment_records)} payment records")
        except Exception as e:
            logger.error(f"Error loading Excel file: {str(e)}")
            self.payment_records = []

    def get_customer_history(self, customer_name: str) -> List[Dict]:
        """Get payment history for a specific customer."""
        try:
            # Case-insensitive partial match for customer name
            matches = [
                record for record in self.payment_records
                if customer_name.lower() in record['customer_name'].lower()
            ]
            return matches
        except Exception as e:
            logger.error(f"Error retrieving customer history: {str(e)}")
            return []

    def get_all_history(self) -> List[Dict]:
        """Get all payment history."""
        return self.payment_records

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
        except:
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
        self.payment_history = PaymentHistory(Config.EXCEL_PATH)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            "🤖 Welcome to the Digital Lending Payment Bot!\n\n"
            "Commands:\n"
            "/qr <user_id> <amount> - Generate a payment QR code\n"
            "/history <customer_name> - View payment history\n"
            "/total <customer_name> - View total amount paid\n"
            "/help - Show this help message\n"
            "/status - Check bot status"
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        await self.start_command(update, context)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command."""
        history_status = "✅ Online" if self.payment_history.payment_records else "❌ Offline"
        status_message = (
            "✅ Bot is running normally\n"
            f"🕒 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Payment History: {history_status}\n"
            "🔄 QR Service: Online"
        )
        await update.message.reply_text(status_message)

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /history command."""
        if not context.args:
            # Show all payment history if no customer name is provided
            history = self.payment_history.get_all_history()
            if history:
                message = "📊 Complete Payment History:\n\n"
                for record in history:
                    message += (
                        f"👤 Customer: {record['customer_name']}\n"
                        f"💰 Amount: ${record['amount']:.2f}\n"
                        f"📅 Date: {record['date']}\n"
                        f"➖➖➖➖➖➖➖➖\n"
                    )
                
                # Split message if it's too long
                if len(message) > 4096:
                    messages = [message[i:i+4096] for i in range(0, len(message), 4096)]
                    for msg in messages:
                        await update.message.reply_text(msg)
                else:
                    await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ No payment history found")
            return

        customer_name = " ".join(context.args)
        history = self.payment_history.get_customer_history(customer_name)

        if history:
            message = f"📊 Payment History for customers matching '{customer_name}':\n\n"
            for record in history:
                message += (
                    f"👤 Customer: {record['customer_name']}\n"
                    f"💰 Amount: ${record['amount']:.2f}\n"
                    f"📅 Date: {record['date']}\n"
                    f"➖➖➖➖➖➖➖➖\n"
                )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(f"❌ No payment history found for '{customer_name}'")

    async def total_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /total command."""
        if not context.args:
            # Show total for all customers if no name is provided
            history = self.payment_history.get_all_history()
            if history:
                total_amount = sum(record['amount'] for record in history)
                message = (
                    "💰 Total Amount for All Customers:\n"
                    f"${total_amount:.2f}\n"
                    f"Number of transactions: {len(history)}"
                )
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ No payment history found")
            return

        customer_name = " ".join(context.args)
        history = self.payment_history.get_customer_history(customer_name)

        if history:
            total_amount = sum(record['amount'] for record in history)
            message = (
                f"💰 Total Amount for customers matching '{customer_name}':\n"
                f"${total_amount:.2f}\n"
                f"Number of transactions: {len(history)}"
            )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(f"❌ No payment history found for '{customer_name}'")

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

            if not self.qr_generator.validate_amount(amount):
                await update.message.reply_text(
                    f"❌ Invalid amount! Amount should be between 0 and {Config.MAX_AMOUNT}"
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
                        f"🔗 PaymentLink:{payment_info}"
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
        application.add_handler(CommandHandler("total", bot.total_command))
        
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