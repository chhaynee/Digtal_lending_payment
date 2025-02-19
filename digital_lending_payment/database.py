import mysql.connector
from datetime import datetime
from typing import List, Dict
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
                SELECT id, userid, amount, 
                       COALESCE(transaction_date, NOW()) as transaction_date,
                       COALESCE(status, 'completed') as status,
                       COALESCE(payment_method, 'QR code') as payment_method,
                       notes
                FROM users 
                WHERE userid = %s 
                ORDER BY transaction_date DESC
            """
            cursor.execute(query, (userid,))
            results = cursor.fetchall()
            
            for result in results:
                if 'transaction_date' in result and result['transaction_date']:
                    result['transaction_date'] = result['transaction_date'].strftime('%Y-%m-%d %H:%M:%S')
            
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
