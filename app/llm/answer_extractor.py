import json

from pydantic import BaseModel

from app.core.config import settings
from app.domain.state import ConversationState
from app.llm.groq_client import get_groq_client


class ExtractedAnswer(BaseModel):
    field: str
    value: str | int | float | bool | None = None
    confidence: float = 0.0


def extract_answer(
    state: ConversationState,
    message: str,
) -> ExtractedAnswer:

    if not state.current_field:
        raise ValueError(
            "Cannot extract an answer without current_field."
        )

    client = get_groq_client()

    prompt = f"""
You are extracting an answer to a chatbot qualification question.

Current qualification field:
{state.current_field}

Customer's message:
{message}

Return ONLY valid JSON:

{{
  "field": "{state.current_field}",
  "value": null,
  "confidence": 0.0
}}

Rules:

1. Extract only information explicitly provided by the customer.
2. Never invent information.
3. Keep the field exactly as provided.
4. If the customer clearly provides an answer, extract it.
5. If the message does not answer the question, return value as null.
6. Confidence must be between 0 and 1.
"""

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Groq returned an empty answer-extraction response."
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Groq returned invalid JSON: {content}"
        ) from exc

    return ExtractedAnswer.model_validate(data)