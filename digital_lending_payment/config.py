# import logging

# # Configure logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# class Config:
#     # TelegramBot setting
#     TELEGRAM_BOT_TOKEN = "7746794164:AAGWR56zZk1xlTK3kp7Ta0vKJw5mim85a4U"

#     #QR code setting
#     GOQR_API_URL = "https://api.qrserver.com/v1/create-qr-code/"
#     QR_CODE_SIZE = "300x300"
#     MAX_AMOUNT = 10000
#     PAYMENT_BASE_URL = "https://pay.ababank.com/yX9JJaKSNv4Jqw7FA"
    
#     # Database configuration
#     DB_HOST = "localhost"
#     DB_USER = "root"
#     DB_PASSWORD = "Det3181"
#     DB_NAME = "demo"
#     DB_PORT = 3306
#     DB_TIMEOUT = 30





import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Config:
    # TelegramBot setting
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    #QR code setting
    GOQR_API_URL = os.getenv("GOQR_API_URL", "https://api.qrserver.com/v1/create-qr-code/")
    QR_CODE_SIZE = os.getenv("QR_CODE_SIZE", "300x300")
    MAX_AMOUNT = float(os.getenv("MAX_AMOUNT", "10000"))
    PAYMENT_BASE_URL = os.getenv("PAYMENT_BASE_URL")
    
    # Database configuration
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))