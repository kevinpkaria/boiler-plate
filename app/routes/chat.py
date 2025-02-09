import os
import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Request, WebSocket
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
from app.routes.bot.summarize import generate_summary

templates = Jinja2Templates(directory="templates")
llm = OpenAI(api_key=os.getenv("DESCGEN_OPENAI_API_KEY"))

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

    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch messages before passing to template
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
    conversation = Conversation(
        conversation_id=conversation_id, company_id=company_id, title="New Chat"
    )
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

    # Get the conversation and check if title needs to be updated
    conversation = db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()
    if conversation and conversation.title == "New Chat":
        messages = await get_conversations(conversation_id)
        if len(messages) >= 2:  # User message + first assistant response
            conversation.title = generate_summary(messages)
            db.commit()

    return HTMLResponse(response["output"])


@router.get("/get-chats")
async def get_chats(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Get all conversation ids for the company
    conversations = company.conversations
    return [
        {"id": conversation.conversation_id, "title": conversation.title}
        for conversation in conversations
    ]


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

# Store connected WebSocket clients
clients = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the connection open
    except:
        clients.remove(websocket)

@router.post("/webhook")
async def webhook_listener(request: Request):
    payload = await request.json()
    event_name = payload.get("eventName")
    role = payload.get("data", {}).get("role")
    thread_id = payload.get("data", {}).get("threadId")

    # Send update to WebSocket clients
    if event_name == "conversations/messages/create" and role == "support":
        message = json.dumps({"refresh": True, "threadId": thread_id})
        for client in clients:
            await client.send_text(message)

    return {"message": "Webhook received"}