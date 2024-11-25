import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # Replace these with your MySQL credentials
    DB_USER = 'root'  # Your MySQL username
    DB_PASSWORD = 'paru1248'  # Your MySQL password
    DB_HOST = 'localhost'  # Your MySQL host
    DB_NAME = 'rideshare_db'  # Your database name
    HUGGINGFACE_API_TOKEN = "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"  # Replace with your actual token
    HUGGINGFACE_MODEL = "mistralai/Mistral-7B-v0.1"
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

    # API settings
    API_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    
    # Recommendation settings
    DEFAULT_RECOMMENDATION_COUNT = 3
    MIN_RIDES_FOR_AI = 5  # Minimum number of rides before using AI recommendations
    
    # Logging settings
    LOG_LEVEL = "INFO"
    
    @classmethod
    def get_huggingface_headers(cls):
        """Get headers for HuggingFace API requests"""
        return {
            "Authorization": f"Bearer {cls.HUGGINGFACE_API_TOKEN}"
        }

    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'a9fb16f9ae90f4c127267933a926fbbc'  # Change this to a secure secret key