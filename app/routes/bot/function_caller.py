import json
import os

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Load tools (functions) from the JSON file
with open("app/routes/bot/tools.json", "r") as file:
    tools = json.load(file)

API_ENDPOINTS = {
    "list_bag_cancellation_reasons": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/shipments/{shipment_id}/bags/{bag_id}/state/{state}/reasons",
    "get_bag": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/bag-details/",
    "list_bags": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/bags",
    "get_channel_configuration": "https://api.fynd.com/service/platform/order-manage/v1.0/company/{company_id}/order-config",
    "get_order": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/order-details?order_id=value",
    "list_orders": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/orders-listing",
    "get_esm_config": "https://api.fynd.com/service/platform/order-manage/v1.0/company/{company_id}/state/manager/config",
    "get_shipment_history": "https://api.fynd.com/service/platform/order-manage/v1.0/company/{company_id}/shipment/history",
    "track_shipment": "https://api.fynd.com/service/platform/order-manage/v1.0/company/{company_id}/tracking",
    "list_shipments": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/shipments-listing",
    "get_shipment_details": "https://api.fynd.com/service/platform/order/v1.0/company/{company_id}/shipment-details",
}


def call_api(function_name, params, company_id, oauth_token):
    """
    Calls the appropriate Fynd API based on the function name.

    Args:
        function_name (str): The API function to call.
        params (dict): The query parameters for the API.
        authorization_token (str): The Bearer token for authorization.

    Returns:
        dict: JSON response or error message.
    """
    # Get the API URL for the function
    url_template = API_ENDPOINTS.get(function_name)
    if not url_template:
        return {"error": f"API URL not found for function '{function_name}'."}

    params["company_id"] = company_id

    headers = {"Authorization": f"Bearer {oauth_token}"}

    # Format URL with path parameters (if any)
    try:
        url = url_template.format(**params)
    except KeyError as e:
        return {"error": f"Missing required parameter: {str(e)}"}

    # new_params = {
    #     k: v
    #     for k, v in params.items()
    #     if (k.replace("_id", "s") not in url)
    #     and (k.replace("_id", "") not in url)
    #     and (str(v).strip() != "")  # Remove empty string values
    # }

    # Make the GET request
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to call {function_name}: {str(e)}"}


def process_openai_function_call(user_query, company_id, oauth_token):
    """
    Processes a user query by calling OpenAI's function-calling API.

    Args:
        user_query (str): The user's input message.

    Returns:
        list: A list of function call dictionaries containing function names and arguments.
    """
    # Prepare the user message
    user_message = {"role": "user", "content": user_query}

    # Call OpenAI API with function calling
    completion = client.chat.completions.create(
        model="gpt-4o", messages=[user_message], tools=tools, tool_choice="required"
    )

    # Extract function call outputs
    function_calls = completion.choices[0].message.tool_calls

    # Process the function call results
    results = []
    for call in function_calls:
        function_name = call.function.name
        arguments = json.loads(call.function.arguments)

        results.append(call_api(function_name, arguments, company_id, oauth_token))

    return results
