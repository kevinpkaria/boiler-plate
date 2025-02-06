from typing import Any, Dict, List, Optional

from app.routes.bot.gpt import get_completion_gpt


def generate_summary(messages: List[Dict[str, Any]]) -> str:
    """
    Generate a 5-6 word summary from the last two messages.
    """
    if len(messages) < 2:
        raise ValueError("At least two messages are required to generate a summary.")

    # Extract the last and second last messages
    last_message = messages[-1]["content"]
    second_last_message = messages[-2]["content"]

    # Construct the prompt
    prompt = (
        f"Summarize the following conversation in 4-5 words where the 1st messsage is user input and 2nd is the assistants response:\n"
        f"1. {second_last_message}\n"
        f"2. {last_message}\n"
    )

    # Call the get_completion_gpt function
    summary = get_completion_gpt(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o",
        temperature=0.5,  # Adjust temperature for creativity
        max_tokens=50,  # Limit tokens to ensure brevity
    )

    return summary
