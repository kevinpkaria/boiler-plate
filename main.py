import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router

app = FastAPI()

# Include routers
app.include_router(chat_router)
app.include_router(auth_router)