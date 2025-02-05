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

from models import Company, SessionLocal

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
    print(f"\n\n{code=}")
    print(f"\n\n{state=}")
    print(f"\n\n{client_id=}")
    print(f"\n\n{company_id=}")
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

            # Store or update company token
            company = (
                db.query(Company)
                .filter(Company.client_id == client_id)
                .first()
            )

            if not company:
                company = Company(
                    company_id=company_id, client_id=client_id
                )
                db.add(company)

            company.auth_code = code
            company.access_token = token_data["access_token"]
            company.refresh_token = token_data.get("refresh_token")
            company.token_type = token_data["token_type"]
            company.expires_at = expires_at
            company.scope = ",".join(token_data["scope"])
            db.commit()
            for c in company.__table__.columns:
                print(f"{c.name}: {getattr(company, c.name)}")
            return RedirectResponse(url=Config.EXTENSION_URL)
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Token generation failed"
            )


@app.get("/refresh")
async def refresh_token(company_id: str, client_id: str, db: Session = Depends(get_db)):
    company = (
        db.query(Company)
        .filter(
            Company.client_id == client_id, Company.company_id == company_id
        )
        .first()
    )

    if not company or not company.refresh_token:
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
        "code": company.auth_code,
        "refresh_token": company.refresh_token,
    }

    async with httpx.AsyncClient() as client:
        print(f"\n\n{Config.BASE_URL}/service/panel/authentication/v1.0/company/{company_id}/oauth/offline-token")
        print(f"\n\n{headers=}")
        print(f"\n\n{payload=}")
        response = await client.post(
            f"{Config.BASE_URL}/service/panel/authentication/v1.0/company/{company_id}/oauth/offline-token",
            headers=headers,
            json=payload,
        )

        if response.status_code == 200:
            token_data = response.json()
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

            company.access_token = token_data["access_token"]
            company.refresh_token = token_data.get(
                "refresh_token", company.refresh_token
            )
            company.expires_at = expires_at
            db.commit()
            return RedirectResponse(url=Config.EXTENSION_URL)
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Token refresh failed"
            )


@app.get("/test")
async def test_api(company_id: str, client_id: str, db: Session = Depends(get_db)):
    company = (
        db.query(Company).filter(Company.client_id == client_id).first()
    )

    if not company or not company.access_token:
        raise HTTPException(status_code=401, detail="No access token available")

    headers = {"Authorization": f"Bearer {company.access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{Config.BASE_URL}/service/platform/order/v1.0/company/{company_id}/shipments-listing",
            headers=headers,
        )
        return response.json()
