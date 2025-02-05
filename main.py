from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from app.routes.chat import router as chat_router
from app.routes.auth import router as auth_router

app = FastAPI()

# Include routers
app.include_router(chat_router)
app.include_router(auth_router)

# Debugging: Print environment variable to verify loading
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")