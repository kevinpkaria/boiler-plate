from app.routes.bot.gpt import get_completion_gpt


def classify_query(input_query: str) -> str:
    """
    Classify the input query into either `BOT` (answer from knowledge base)
    or `API` (fetch order details from an API).
    """
    prompt = f"""
    Classify the following query into one of two categories: `BOT` or `API`.

    Guidelines:
    - If the query is a general question about policies, platform usage, seller guidelines, or FAQs, classify it as `BOT`.
        - Example queries:
            - "What are the seller commission charges?"
            - "How do I list a new product?"
            - "What is the return policy?"
            - "How do I contact support?"
    - If the query is related to order details, tracking, shipment updates, or anything requiring an API call, classify it as `API`.
        - Example queries:
            - "Where is my order?"
            - "What is the status of my shipment?"
            - "Track my order"
            - "Update my shipping address"
            - "Reassign my order location"

    **Available APIs for fetching order details:**
    
    1. **List bag cancellation reasons** - Get reasons to perform full or partial cancellation of a bag.
    2. **Get bag** - Retrieve detailed information about a specific bag.
    3. **List bags** - Get a paginated list of bags based on provided filters.
    4. **Get channel configuration** - Retrieve configuration settings specific to orders for a channel.
    5. **Get order** - Get detailed information about a specific order.
    6. **List orders** - Get a list of orders based on provided filters.
    7. **Retrieve ESM config** - Get Entity State Manager configuration details for order processing.
    8. **Get a shipment's history** - Retrieve shipment history logs.
    9. **Track shipment** - Get courier tracking details using shipment ID or AWB number.
    10. **List shipments** - Get a list of shipments based on filters.
    11. **Get shipment details** - Retrieve detailed information about a specific shipment.

    Input Query: {input_query}
    """

    # Prepare messages for the GPT model
    messages = [
        {
            "role": "system",
            "content": (
                "Classify user input into one of the following categories: `BOT` or `API`. "
                "Use these rules: "
                "- Classify as `BOT` if the input is a general FAQ or support question. "
                "- Classify as `API` if the input is related to order tracking, shipment details, or requires an API call."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    # Get the classification from the GPT model
    response = get_completion_gpt(
        messages=messages,
        model="gpt-4o",
        response_format={"type": "text"},
        max_tokens=15,
    )

    return response
