import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv('BACKEND_HOST', 'http://localhost:8000/')

BACKEND_JWT_SECRET_KEY = os.getenv('BACKEND_JWT_SECRET_KEY', '')
