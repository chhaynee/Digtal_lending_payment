import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Config:
    # TelegramBot setting
    TELEGRAM_BOT_TOKEN = "7746794164:AAGWR56zZk1xlTK3kp7Ta0vKJw5mim85a4U"

    #QR code setting
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