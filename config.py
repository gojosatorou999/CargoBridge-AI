import os
from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cargobridge-dev-secret-change-in-prod-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

    # Twilio
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

    # AIS
    AIS_API_KEY = os.environ.get('AIS_API_KEY', '')
    AISSTREAM_API_KEY = os.environ.get('AISSTREAM_API_KEY', '')

    # APScheduler
    SCHEDULER_API_ENABLED = False


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'cargobridge.db')}"
    )


class ProductionConfig(Config):
    DEBUG = False
    _raw_db_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or os.environ.get('POSTGRES_PRISMA_URL', '')
    # Vercel Postgres / Neon may prefix with postgres:// — SQLAlchemy needs postgresql://
    _is_postgres = bool(_raw_db_url)
    SQLALCHEMY_DATABASE_URI = _raw_db_url.replace('postgres://', 'postgresql://', 1) if _raw_db_url else 'sqlite:///cargobridge_prod.db'
    # NullPool: do NOT reuse connections across serverless invocations.
    # Without this, Vercel/Neon serverless connections time out after the
    # first request finishes and every subsequent request gets a broken conn.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': NullPool,
        # connect_timeout only valid for PostgreSQL / psycopg2
        **({'connect_args': {'connect_timeout': 10}} if _is_postgres else {}),
    }


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
