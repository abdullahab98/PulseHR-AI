import logging
from pymongo import MongoClient
from pymongo.database import Database
from app.config import settings

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self):
        self.client: MongoClient = None
        self.db: Database = None

    def connect(self):
        """Establish connection to MongoDB Atlas."""
        if not settings.MONGODB_URL:
            logger.warning("MONGODB_URL is not set in configuration.")
            return None
        try:
            self.client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
            # Verify connection with ping
            self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DB_NAME]
            logger.info(f"Successfully connected to MongoDB Atlas database: '{settings.MONGODB_DB_NAME}'")
            return self.db
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            self.client = None
            self.db = None
            return None

    def get_database(self) -> Database:
        """Returns the active MongoDB database instance."""
        if self.db is None:
            return self.connect()
        return self.db

    def close(self):
        """Close MongoDB connection client."""
        if self.client:
            self.client.close()
            logger.info("MongoDB client connection closed.")

mongo_manager = MongoDBManager()
