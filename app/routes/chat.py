from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import AsyncGenerator
from openai import OpenAI
import os

from app.models import SessionLocal

print(f"\n\n{os.getenv('OPENAI_API_KEY')=}\n\n")
templates = Jinja2Templates(directory="templates")
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.post("/chat")
async def chat(message: str = Form(...), db: Session = Depends(get_db)):
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            system_prompt = """You are a helpful Fynd Seller Support Assistant."""
            yield f'<div class="message user">{message}</div>'
            yield '<div class="message assistant">'
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