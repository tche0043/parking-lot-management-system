import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Database configuration
    DB_SERVER = os.environ.get('DB_SERVER') or 'localhost'
    DB_DATABASE = os.environ.get('DB_DATABASE') or 'ParkingLot'
    DB_USERNAME = os.environ.get('DB_USERNAME') or 'sa'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'p@ssw0rd'
    
    # Build database connection string for Docker SQL Server using pymssql
    DATABASE_URI = f"mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/{DB_DATABASE}"
    
    # Database port (default 1433 for SQL Server)
    DB_PORT = os.environ.get('DB_PORT') or '1433'
    
    # For Docker connections, include port if not default
    if DB_PORT != '1433':
        DATABASE_URI = f"mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_DATABASE}"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}