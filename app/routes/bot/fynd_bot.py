import os

import httpx
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TIMEOUT_SECONDS = 60.0

base_url = os.getenv("COPILOT_BASE_URL")

# Headers for the API requests, including authentication
headers = {
    "accept": "application/json",
    "x-integration-id": os.getenv("COPILOT_INTEGRATION_ID"),
    "x-integration-token": os.getenv("COPILOT_INTEGRATION_TOKEN"),
    "Content-Type": "application/json",
}

# User ID for the API requests
user_id = os.getenv("COPILOT_USER_ID")

# Default title for the conversation
title = "FyndBotQuery"


async def get_conversations(conversation_id: int):
    """
    Get all conversations for a company.
    """
    url = f"{base_url}/conversations/{conversation_id}/messages"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url, headers=headers, timeout=httpx.Timeout(TIMEOUT_SECONDS, read=None)
        )
        response.raise_for_status()
        response = response.json()
        messages = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in response["items"]
        ]
        return messages[::-1]


async def create_conversation(company_id: int):
    """
    Create a new conversation with the API.

    Returns:
        dict: JSON response from the API containing conversation details.
    """
    url = f"{base_url}/conversations"
    meta = {"company_id": company_id}
    data = {"title": title, "userId": user_id, "meta": meta}
    # Send POST request to create a conversation
    # response = requests.post(url, headers=headers, json=data)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, headers=headers, json=data, timeout=httpx.Timeout(TIMEOUT_SECONDS, read=None)
        )
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()


async def send_message(query, conversation_id):
    """
    Send a message to a specific conversation.

    Args:
        query (str): The message content to send.
        conversation_id (str): The ID of the conversation.

    Returns:
        dict: JSON response from the API containing the message details.
    """
    url = f"{base_url}/conversations/{conversation_id}/messages"
    params = {"wait": "true", "generateAssistantMessage": "true"}
    data = {"content": query, "role": "user", "userId": user_id}

    # # Send POST request to send a message
    # response = requests.post(url, headers=headers, params=params, json=data)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            params=params,
            json=data,
            timeout=httpx.Timeout(TIMEOUT_SECONDS, read=None),
        )
        response.raise_for_status()  # Raise an error for bad responses

    return response.json()


async def process_query(query, conversation_id):
    """
    Process a query by sending it to the conversation and returning the response.

    Args:
        query (str): The query to process.
        conversation_id (str): The ID of the conversation.

    Returns:
        dict: A dictionary containing the output or an error message.
    """
    # Send the message and get the response
    message_response = await send_message(query, conversation_id)
    reply_content = message_response["reply"]["content"]
    return {"output": reply_content}
