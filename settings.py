import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv('BACKEND_HOST', 'http://localhost:8000/')
