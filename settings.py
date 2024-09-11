import os
from dotenv import load_dotenv

base_path = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(base_path, '.env'))

BACKEND_HOST = os.getenv('BACKEND_HOST', 'http://localhost:8000/')

BACKEND_JWT_SECRET_KEY = os.getenv('BACKEND_JWT_SECRET_KEY', '')
