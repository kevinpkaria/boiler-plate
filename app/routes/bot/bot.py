# main.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.routes.bot.classify_intent import classify_query
from app.routes.bot.function_caller import process_openai_function_call
from app.routes.bot.fynd_bot import create_conversation, process_query

router = APIRouter()


@router.post("/create-conversation/")
async def create_conversation_bolticbot(company_id: int, oauth_token: str):
    """Route to interact with BolticBot"""
    try:
        response = create_conversation(company_id, oauth_token)
        return JSONResponse(content=response, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/process/")
async def read_query(query: str, conversation_id: str):
    # result = classify_query(query)
    # if result == "BOT":
    #     result = process_query(query, conversation_id)
    # else:
    #     result = process_openai_function_call(query, company_id, oauth_token)
    # return {"result": result}
    result = process_query(query, conversation_id)
    return result
