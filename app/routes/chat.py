import os
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import Company, Conversation, SessionLocal
from app.routes.auth import Config
from app.routes.bot.fynd_bot import (
    create_conversation,
    get_conversations,
    process_query,
)

templates = Jinja2Templates(directory="templates")
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/home", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    company_id: str,
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not conversation_id:
        return RedirectResponse(
            url=f"{Config.EXTENSION_URL}/new-chat?company_id={company_id}"
        )

    # Fetch all messages for the given conversation_id
    messages = await get_conversations(conversation_id)

    # Pass the messages to the template
    return templates.TemplateResponse(
        "chat.html", {"request": request, "messages": messages}
    )


@router.get("/new-chat")
async def new_chat(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    response = await create_conversation(company_id)
    conversation_id = response["id"]
    conversation = Conversation(conversation_id=conversation_id, company_id=company_id)
    db.add(conversation)
    db.commit()
    return RedirectResponse(
        url=f"{Config.EXTENSION_URL}/home?company_id={company_id}&conversation_id={conversation_id}"
    )


@router.post("/chat")
async def chat(
    conversation_id: str,
    company_id: Optional[str] = None,
    message: str = Form(...),
    db: Session = Depends(get_db),
):
    response = await process_query(message, conversation_id)
    if not response.get("output"):
        raise HTTPException(status_code=400, detail="Error processing query")
    return HTMLResponse(response["output"])


@router.get("/get-chats")
async def get_chats(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Get all conversation ids for the company
    conversations = company.conversations
    return [conversation.conversation_id for conversation in conversations]


@router.delete("/conversation")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
