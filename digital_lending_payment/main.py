from telegram.ext import ApplicationBuilder, CommandHandler
from config import Config, logger
from database import PaymentDatabase
from bot import PaymentBot

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