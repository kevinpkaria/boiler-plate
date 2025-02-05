import base64
import os
import secrets
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.models import Company, SessionLocal

router = APIRouter()


class Config:
    API_KEY = os.getenv("FYND_API_KEY")
    API_SECRET = os.getenv("FYND_API_SECRET")
    EXTENSION_URL = os.getenv("EXTENSION_URL")
    BASE_URL = os.getenv("BASE_URL")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/fp/install")
async def handle_install(
    company_id: str, client_id: str, cluster_url: str, db: Session = Depends(get_db)
):
    state = secrets.token_urlsafe(16)
    print("\n\n", Config.EXTENSION_URL, "\n\n")
    auth_url = (
        f"{Config.BASE_URL}/service/panel/authentication/v1.0/company/{company_id}/oauth/authorize"
        f"?client_id={Config.API_KEY}"
        f"&redirect_uri={Config.EXTENSION_URL}/fp/auth"
        f"&response_type=code"
        f"&scope=company/product,company/order"
        f"&state={state}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/fp/auth")
async def handle_auth(
    code: str,
    state: str,
    client_id: str,
    company_id: str,
    db: Session = Depends(get_db),
):
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
            company = db.query(Company).filter(Company.client_id == client_id).first()
            if not company:
                company = Company(company_id=company_id, client_id=client_id)
                db.add(company)
            company.auth_code = code
            company.access_token = token_data["access_token"]
            company.refresh_token = token_data.get("refresh_token")
            company.token_type = token_data["token_type"]
            company.expires_at = expires_at
            company.scope = ",".join(token_data["scope"])
            db.commit()
            return RedirectResponse(url=Config.EXTENSION_URL)
        else:
            raise HTTPException(
                status_code=response.status_code, detail="Token generation failed"
            )


@router.get("/refresh")
async def refresh_token(company_id: str, client_id: str, db: Session = Depends(get_db)):
    company = (
        db.query(Company)
        .filter(Company.client_id == client_id, Company.company_id == company_id)
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


@router.get("/test")
async def test_api(company_id: str, client_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.client_id == client_id).first()
    if not company or not company.access_token:
        raise HTTPException(status_code=401, detail="No access token available")
    headers = {"Authorization": f"Bearer {company.access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{Config.BASE_URL}/service/platform/order/v1.0/company/{company_id}/shipments-listing",
            headers=headers,
        )
        return response.json()
