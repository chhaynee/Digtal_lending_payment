import mysql.connector
from datetime import datetime
from typing import List, Dict, Optional
from config import Config, logger

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
                auth_plugin='mysql_native_password'
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
                SELECT id, userid, amount
                FROM users 
                WHERE userid = %s 
                ORDER BY id DESC
            """
            cursor.execute(query, (userid,))
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} transactions for user {userid}")
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error retrieving user history: {str(e)}")
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
            
            for result in results:
                if 'transaction_date' in result and result['transaction_date']:
                    result['transaction_date'] = result['transaction_date'].strftime('%Y-%m-%d %H:%M:%S')
            
            return results
        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            return []
        
    def store_payment(self, userid: str, amount: float) -> bool:
        """Store payment details after QR generation."""
        if not self.ensure_connection():
            logger.error("Failed to connect to database")
            return False
            
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO users (userid, amount)
                VALUES (%s, %s)
            """
            cursor.execute(query, (userid, str(amount)))
            self.connection.commit()
            cursor.close()
            logger.info(f"Stored payment for user {userid} with amount ${amount}")
            return True
        except Exception as e:
            logger.error(f"Error storing payment: {str(e)}")
            return False

    def get_latest_payment(self) -> Optional[Dict]:
        """Get the most recent payment (admin only)."""
        if not self.ensure_connection():
            logger.error("Failed to connect to database")
            return None
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT id, userid, amount
                FROM users 
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"Error retrieving latest payment: {str(e)}")
            return None

    # def get_user_latest_payment(self, userid: str) -> Optional[Dict]:
    #     """Get the most recent payment for a specific user."""
    #     if not self.ensure_connection():
    #         logger.error("Failed to connect to database")
    #         return None
            
    #     try:
    #         cursor = self.connection.cursor(dictionary=True)
    #         query = """
    #             SELECT id, userid, amount
    #             FROM users 
    #             WHERE userid = %sSELECT * FROM users;
    #             ORDER BY id DESC 
    #             LIMIT 1
    #         """
    #         cursor.execute(query, (userid,))
    #         result = cursor.fetchone()
    #         cursor.close()
    #         logger.info(f"Retrieved latest payment for user {userid}")
    #         return result
    #     except Exception as e:
    #         logger.error(f"Error retrieving user's latest payment: {str(e)}")
    #         return None
    def get_user_latest_payment(self, userid: str) -> Optional[Dict]:
        """Get the most recent payment for a specific user."""
        if not self.ensure_connection():
            logger.error("Failed to connect to database")
            return None
            
        try:
            cursor = self.connection.cursor(dictionary=True)
            # Fixed SQL injection vulnerability by removing the stray "SELECT * FROM users;"
            query = """
                SELECT id, userid, amount
                FROM users 
                WHERE userid = %s
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(query, (userid,))
            result = cursor.fetchone()
            cursor.close()
            logger.info(f"Retrieved latest payment for user {userid}")
            return result
        except Exception as e:
            logger.error(f"Error retrieving user's latest payment: {str(e)}")
            return None