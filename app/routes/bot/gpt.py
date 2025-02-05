import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)


def get_completion_gpt(
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o",
    temperature: float = 0,
    max_tokens: int = 1024,
    tools: Optional[List[Dict[str, Any]]] = None,
    response_format: Optional[Dict[str, Any]] = {"type": "json_object"},
    seed: Optional[int] = 143,
    tool_choice=None,
) -> str:
    """
    Get a completion from GPT-4 model with structured JSON output.
    """
    # model = "deepseek-chat"
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        tools=tools,
        seed=seed,
        tool_choice=tool_choice,
    )
    print(f"[INFO] >>> GPT_4o call usage : {response.to_dict()}")
    return response.choices[0].message.content
