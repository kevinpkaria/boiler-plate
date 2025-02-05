import base64
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

import anthropic
import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from openai import OpenAI

from models import MerchantToken, SessionLocal, StateStore

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize OpenAI client
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
class Config:
    API_KEY = os.getenv("FYND_API_KEY", "67a1fb44d215866dcb2d9756")
    API_SECRET = os.getenv("FYND_API_SECRET", "b..QPpOO1z8alQq")
    EXTENSION_URL = os.getenv(
        "EXTENSION_URL", "https://2efc-125-22-87-250.ngrok-free.app"
    )
    BASE_URL = "https://api.fynd.com"


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Chat interface routes
@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/chat")
async def chat(message: str = Form(...), db: Session = Depends(get_db)):
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            system_prompt = (
                """You are a helpful Fynd Seller Support Assistant."""
            )

            # Send initial HTML for user message
            yield f'<div class="message user">{message}</div>'

            # Start assistant message container
            yield '<div class="message assistant">'

            # Use OpenAI to generate a response
            stream = llm.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=1024,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

            # Close assistant message container
            yield '</div>'
            
        except Exception as e:
            yield f'<div class="message assistant">Error: {str(e)}</div>'

    return StreamingResponse(
        generate_response(),
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/html; charset=utf-8"
        }
    )


# OAuth routes
@app.get("/fp/install")
async def handle_install(
    company_id: str, client_id: str, cluster_url: str, db: Session = Depends(get_db)
):
    # Generate state parameter
    state = secrets.token_urlsafe(16)

    # Store state and installation parameters
    state_entry = StateStore(state=state, company_id=company_id, client_id=client_id)
    db.add(state_entry)
    db.commit()

    # Construct authorization URL
    auth_url = (
        f"{Config.BASE_URL}/service/panel/authentication/v1.0/company/{company_id}/oauth/authorize"
        f"?client_id={Config.API_KEY}"
        f"&redirect_uri={Config.EXTENSION_URL}/fp/auth"
        f"&response_type=code"
        f"&scope=company/product,company/order"
        f"&state={state}"
    )
    return RedirectResponse(url=auth_url)


@app.get("/fp/auth")
async def handle_auth(
    code: str,
    state: str,
    client_id: str,
    company_id: str,
    db: Session = Depends(get_db),
):
    # Validate state and client_id
    state_entry = (
        db.query(StateStore)
        .filter(
            StateStore.state == state,
            StateStore.client_id == client_id,
            StateStore.company_id == company_id,
        )
        .first()
    )

    if not state_entry:
        raise HTTPException(
            status_code=400, detail="Invalid state or client parameters"
        )

    # Update state entry with auth code
    state_entry.auth_code = code
    db.commit()

    # Get offline token
    return await get_offline_token(company_id, code, client_id, db)


async def get_offline_token(company_id: str, code: str, client_id: str, db: Session):
    auth_string = base64.b64encode(
        f"{Config.API_KEY}:{Config.API_SECRET}".encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {auth_string}",
        "Content-Type": "application/json",
    }

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": Config.API_KEY,
        "client_secret": Config.API_SECRET,
        "scope": "company/product,company/order",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{Config.BASE_URL}/service/panel/authentication/v1.0/company/{company_id}/oauth/offline-token",
            headers=headers,
            json=payload,
        )

        if response.status_code == 200:
            token_data = response.json()
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

            # Store or update merchant token
            merchant_token = (
                db.query(MerchantToken)
                .filter(MerchantToken.client_id == client_id)
                .first()
            )

            if not merchant_token:
                merchant_token = MerchantToken(
                    company_id=company_id, client_id=client_id
                )
                db.add(merchant_token)

            merchant_token.access_token = token_data["access_token"]
            merchant_token.refresh_token = token_data.get("refresh_token")
            merchant_token.token_type = token_data["token_type"]
            merchant_token.expires_at = expires_at
            merchant_token.scope = ",".join(token_data["scope"])
            db.commit()
            return RedirectResponse(url=Config.EXTENSION_URL)
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Token generation failed"
            )


@app.get("/refresh")
async def refresh_token(company_id: str, client_id: str, db: Session = Depends(get_db)):
    merchant_token = (
        db.query(MerchantToken)
        .filter(
            MerchantToken.client_id == client_id, MerchantToken.company_id == company_id
        )
        .first()
    )

    state_store = (
        db.query(StateStore)
        .filter(StateStore.client_id == client_id, StateStore.company_id == company_id)
        .first()
    )

    if not merchant_token or not merchant_token.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")

    auth_string = base64.b64encode(
        f"{Config.API_KEY}:{Config.API_SECRET}".encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {auth_string}",
        "Content-Type": "application/json",
    }

    payload = {
        "grant_type": "refresh_token",
        "code": state_store.auth_code,
        "refresh_token": merchant_token.refresh_token,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{Config.BASE_URL}/service/panel/authentication/v1.0/company/{company_id}/oauth/offline-token",
            headers=headers,
            json=payload,
        )

        if response.status_code == 200:
            token_data = response.json()
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

            merchant_token.access_token = token_data["access_token"]
            merchant_token.refresh_token = token_data.get(
                "refresh_token", merchant_token.refresh_token
            )
            merchant_token.expires_at = expires_at
            db.commit()
            return RedirectResponse(url=Config.EXTENSION_URL)
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Token refresh failed"
            )


@app.get("/test")
async def test_api(company_id: str, client_id: str, db: Session = Depends(get_db)):
    merchant_token = (
        db.query(MerchantToken).filter(MerchantToken.client_id == client_id).first()
    )

    if not merchant_token or not merchant_token.access_token:
        raise HTTPException(status_code=401, detail="No access token available")

    headers = {"Authorization": f"Bearer {merchant_token.access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{Config.BASE_URL}/service/platform/order/v1.0/company/{company_id}/shipments-listing",
            headers=headers,
        )
        return response.json()
