import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import admin config from config/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))
from admin_config import ADMIN_USERNAME, ADMIN_PASSWORD, AUTO_LOGIN, SECRET_KEY


class Config:
    SECRET_KEY = SECRET_KEY
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'piano_jazz_videos.db')
    ADMIN_USERNAME = ADMIN_USERNAME
    ADMIN_PASSWORD = ADMIN_PASSWORD
    AUTO_LOGIN = AUTO_LOGIN
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    YOUTUBE_CLIENT_SECRET_PATH = os.path.join(
        os.path.dirname(__file__), '..', 'config',
        'client_secret_669231030065-of0u2ovg4sqs69ho0r70m9a3so5obmm6.apps.googleusercontent.com.json'
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
