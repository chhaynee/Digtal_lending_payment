import re
import requests
from typing import Optional
from io import BytesIO
from config import Config, logger

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