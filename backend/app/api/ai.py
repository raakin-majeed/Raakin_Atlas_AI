import os
from typing import Any, Dict

from fastapi import APIRouter
from groq import Groq

from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_groq_api_key() -> str:
    return (settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")).strip()


def run_agent(system_prompt: str, user_input: str) -> str:
    api_key = _get_groq_api_key()
    if not api_key:
        return "Error: GROQ_API_KEY is not configured"
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return "Error: {0}".format(str(e))


@router.post("/run-agent")
async def run_agent_endpoint(payload: Dict[str, Any]) -> Dict[str, str]:
    system_prompt = str(payload.get("system_prompt", "You are a helpful assistant."))
    user_input = str(payload.get("user_input", ""))
    output = run_agent(system_prompt, user_input)
    return {"output": output}