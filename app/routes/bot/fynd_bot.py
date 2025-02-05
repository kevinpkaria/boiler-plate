import os

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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


def create_conversation(company_id: int, oauth_token: str):
    """
    Create a new conversation with the API.

    Returns:
        dict: JSON response from the API containing conversation details.
    """
    url = f"{base_url}/conversations"
    meta = {"company_id": company_id, "authorization_token": oauth_token}
    data = {"title": title, "userId": user_id, "meta": meta}
    # Send POST request to create a conversation
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Raise an error for bad responses

    return response.json()


def send_message(query, conversation_id):
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

    # Send POST request to send a message
    response = requests.post(url, headers=headers, params=params, json=data)
    response.raise_for_status()  # Raise an error for bad responses

    return response.json()


def process_query(query, conversation_id):
    """
    Process a query by sending it to the conversation and returning the response.

    Args:
        query (str): The query to process.
        conversation_id (str): The ID of the conversation.

    Returns:
        dict: A dictionary containing the output or an error message.
    """
    try:
        # Send the message and get the response
        message_response = send_message(query, conversation_id)
        reply_content = message_response["reply"]["content"]
        return {"output": reply_content}
    except Exception as e:
        # Log the error and return an error message
        logger.error(f"Error processing query: {e}")
        return {"error": "An error occurred while processing your request."}
